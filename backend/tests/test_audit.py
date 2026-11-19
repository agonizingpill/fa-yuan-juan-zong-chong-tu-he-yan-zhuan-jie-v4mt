import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.database import Base,engine,Session
from src.models import User,Intake,Consent,Triage
from src.auth import password_hash

@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        with Session() as db:
            for role in ('operator','supervisor','viewer'):
                db.add(User(username=role,password=password_hash('Aid@2026'),role=role))
            db.commit()
        yield c

def auth(client,username='supervisor'):
    r=client.post('/auth/login',json={'username':username,'password':'Aid@2026'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def make_case(code,predicted,confidence,status='done'):
    with Session() as db:
        case=Intake(code=code,alias='测试'+code,facts=f'{code} 模拟来访事实描述，用于抽检复核')
        db.add(case);db.flush()
        db.add(Consent(intake_id=case.id,authorized=True,basis='测试授权存根'))
        db.add(Triage(intake_id=case.id,facts_version=1,status=status,predicted=predicted,confidence=confidence,manual_required=confidence<.68))
        db.commit()
        return case.id

def make_batch(client,size=10,seed=7):
    r=client.post('/audit-batches',json={'sample_size':size,'seed':seed},headers=auth(client))
    assert r.status_code==200,r.text
    return r.json()

def determine(client,sample_id,topic):
    return client.post(f'/audit-samples/{sample_id}/determine',json={'topic':topic},headers=auth(client))

def revise_facts(client,intake_id,facts='更正后的模拟事实描述，版本已更新'):
    r=client.patch(f'/intakes/{intake_id}/facts',json={'facts':facts},headers=auth(client))
    assert r.status_code==200,r.text

def test_stratified_sampling_and_blind_review(client):
    cases=[make_case('A1','labor',.95),make_case('A2','labor',.93),make_case('B1','housing',.75),
           make_case('C1','consumer',.5),make_case('C2','consumer',.4),make_case('C3','consumer',.3)]
    batch=make_batch(client)
    assert batch['status']=='open' and batch['seed']==7
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    assert detail['total']==6 and detail['determined']==0 and detail['stale']==0
    assert 'strata' not in detail,'复核未办完不能出分层成绩'
    for s in detail['samples']:
        assert 'recommended' not in s and 'confidence' not in s and 'topic' not in s,'定题前不得看到原推荐'
        assert s['facts_snapshot'] and s['attempts']==0
    listed=client.get('/audit-batches',headers=auth(client,'viewer')).json()
    assert listed[0]['total']==6,'只读员可查看进度'
    r=client.post('/audit-batches',json={'sample_size':5},headers=auth(client,'viewer'))
    assert r.status_code==403,'只读员不能建批'
    r=client.post('/audit-batches',json={'sample_size':5},headers=auth(client,'operator'))
    assert r.status_code==403,'接待员不能建批'

def test_determine_retry_and_weighted_score(client):
    make_case('A1','labor',.95);make_case('A2','labor',.93);make_case('B1','housing',.75)
    make_case('C1','consumer',.5);make_case('C2','consumer',.4);make_case('C3','consumer',.3)
    batch=make_batch(client)
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    by_code={s['code']:s for s in detail['samples']}
    r=client.post(f"/audit-batches/{batch['id']}/seal",headers=auth(client))
    assert r.status_code==409 and '未核定' in r.json()['detail'],'复核未办完不出成绩'
    plan={'A1':'labor','A2':'housing','B1':'housing','C1':'labor','C2':'consumer','C3':'consumer'}
    for code,topic in plan.items():
        r=determine(client,by_code[code]['id'],topic)
        assert r.status_code==200,r.text
    revealed=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    assert all('recommended' in s for s in revealed['samples']),'定题后揭晓原推荐'
    r=determine(client,by_code['A1']['id'],'labor')
    assert r.status_code==200 and r.json()['attempts']==2,'重试只记次数'
    sealed=client.post(f"/audit-batches/{batch['id']}/seal",headers=auth(client)).json()
    assert sealed['status']=='sealed'
    assert sealed['rate_low']==pytest.approx(1/3),'错分2/6按层加权，重试不重复计分'
    assert sealed['rate_high']==pytest.approx(1/3),'无缺样时上下界相同'
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    strata={(s['topic'],s['tier']):s for s in detail['strata']}
    assert strata[('labor','high')]['population']==2 and strata[('labor','high')]['errors']==1
    assert strata[('housing','mid')]['population']==1 and strata[('housing','mid')]['errors']==0
    assert strata[('consumer','low')]['population']==3 and strata[('consumer','low')]['errors']==1
    r=client.post(f"/audit-batches/{batch['id']}/seal",headers=auth(client))
    assert r.status_code==409,'重复封批被拒绝'
    r=determine(client,by_code['A1']['id'],'housing')
    assert r.status_code==409,'封批后不能再核定'

def test_missing_samples_and_bounds(client):
    d1=make_case('D1','labor',.85);d2=make_case('D2','labor',.8);e1=make_case('E1','housing',.5)
    batch=make_batch(client)
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    by_code={s['code']:s for s in detail['samples']}
    assert determine(client,by_code['D1']['id'],'labor').status_code==200
    revise_facts(client,d2)
    r=determine(client,by_code['D2']['id'],'labor')
    assert r.status_code==409 and '缺样' in r.json()['detail'],'封批前更正事实的卷记为缺样'
    assert determine(client,by_code['E1']['id'],'consumer').status_code==200
    sealed=client.post(f"/audit-batches/{batch['id']}/seal",headers=auth(client)).json()
    assert sealed['rate_low']==pytest.approx(1/3),'缺样全对：(2*0/2+1*1/1)/3'
    assert sealed['rate_high']==pytest.approx(2/3),'缺样全错：(2*1/2+1*1/1)/3'
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    d2view=[s for s in detail['samples'] if s['code']=='D2'][0]
    assert d2view['missing'] is True

def test_correction_after_determination_counts_as_missing(client):
    f1=make_case('F1','consumer',.95)
    batch=make_batch(client)
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    sample=detail['samples'][0]
    assert determine(client,sample['id'],'labor').status_code==200
    revise_facts(client,f1)
    sealed=client.post(f"/audit-batches/{batch['id']}/seal",headers=auth(client)).json()
    assert sealed['status']=='sealed','核定后更正不阻塞封批'
    assert sealed['rate_low']==0 and sealed['rate_high']==1,'同时送达以封批时事实版本为准，核定不计分'
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    assert detail['samples'][0]['missing'] is True and detail['samples'][0]['determined']=='labor'

def test_frame_excludes_open_batch_and_stale_triage(client):
    g1=make_case('G1','labor',.95,status='reviewed')
    h1=make_case('H1','housing',.95)
    revise_facts(client,h1)
    batch=make_batch(client,size=10)
    detail=client.get(f"/audit-batches/{batch['id']}",headers=auth(client)).json()
    assert [s['code'] for s in detail['samples']]==['G1'],'已复核主题可入样，版本不符的分流不入样'
    r=client.post('/audit-batches',json={'sample_size':5},headers=auth(client))
    assert r.status_code==409,'开放批次占用中的卷不重复入样'
    assert determine(client,detail['samples'][0]['id'],'labor').status_code==200
    assert client.post(f"/audit-batches/{batch['id']}/seal",headers=auth(client)).status_code==200
    batch2=make_batch(client,size=10,seed=9)
    assert batch2['id']!=batch['id'],'封批后卷可重新入样'

def test_proportional_allocation(client):
    for i in range(4):make_case(f'L{i}','labor',.95)
    for i in range(2):make_case(f'H{i}','housing',.8)
    batch=make_batch(client,size=3,seed=3)
    with Session() as db:
        from sqlalchemy import select
        from src.models import AuditStratum
        strata={(s.topic,s.tier):s for s in db.scalars(select(AuditStratum).where(AuditStratum.batch_id==batch['id']))}
    assert strata[('labor','high')].population==4 and strata[('labor','high')].sample_size==2
    assert strata[('housing','mid')].population==2 and strata[('housing','mid')].sample_size==1

def test_seed_reproducible(client):
    for i in range(5):make_case(f'R{i}','labor',.95)
    first=make_batch(client,size=3,seed=42)
    detail=client.get(f"/audit-batches/{first['id']}",headers=auth(client)).json()
    picked=sorted(s['intake_id'] for s in detail['samples'])
    for s in detail['samples']:assert determine(client,s['id'],'labor').status_code==200
    assert client.post(f"/audit-batches/{first['id']}/seal",headers=auth(client)).status_code==200
    second=make_batch(client,size=3,seed=42)
    detail=client.get(f"/audit-batches/{second['id']}",headers=auth(client)).json()
    assert sorted(s['intake_id'] for s in detail['samples'])==picked,'同种子同抽样框应复现同样本'
