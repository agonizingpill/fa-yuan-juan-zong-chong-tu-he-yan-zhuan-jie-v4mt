import random,secrets
from sqlalchemy import select
from .models import AuditBatch,AuditStratum,AuditSample,Intake,Triage,now
from .constants import AuditBatchState
from .common import get,reject,finish,dump
TIER_EDGES=(('low',.68),('mid',.9),('high',1.01))
def tier_of(confidence):
    for tier,edge in TIER_EDGES:
        if confidence<edge:return tier
    return 'high'
def frame(db):
    busy=set(db.scalars(select(AuditSample.intake_id).join(AuditBatch,AuditSample.batch_id==AuditBatch.id).where(AuditBatch.status==AuditBatchState.open.value)))
    rows=[]
    for case in db.scalars(select(Intake).order_by(Intake.id)):
        if case.id in busy:continue
        t=db.scalar(select(Triage).where(Triage.intake_id==case.id,Triage.facts_version==case.facts_version,Triage.status.in_(['done','reviewed'])).order_by(Triage.id.desc()))
        if t and t.predicted:rows.append((case,t))
    return rows
def allocate(pool,size):
    keys=[k for k,v in pool.items() if v]
    total=sum(len(pool[k]) for k in keys);size=min(size,total)
    alloc={k:0 for k in keys}
    if size>=len(keys):
        for k in keys:alloc[k]=1
    quota={k:len(pool[k])*size/total for k in keys}
    remaining=size-sum(alloc.values())
    while remaining>0:
        progressed=False
        for k in sorted(keys,key=lambda k:quota[k]-alloc[k],reverse=True):
            if remaining<=0:break
            if alloc[k]<len(pool[k]):alloc[k]+=1;remaining-=1;progressed=True
        if not progressed:break
    return {k:v for k,v in alloc.items() if v>0}
def create(db,data,user):
    pool={}
    for case,t in frame(db):pool.setdefault((t.predicted,tier_of(t.confidence)),[]).append((case,t))
    reject(not pool,'当前没有可抽样的已分流卷宗')
    seed=data.seed if data.seed is not None else secrets.randbelow(2**31)
    rng=random.Random(seed)
    batch=AuditBatch(seed=seed,created_by=user.username);db.add(batch);db.flush()
    for (topic,tier),n in allocate(pool,data.sample_size).items():
        items=pool[(topic,tier)]
        db.add(AuditStratum(batch_id=batch.id,topic=topic,tier=tier,population=len(items),sample_size=n))
        for case,t in rng.sample(items,n):
            db.add(AuditSample(batch_id=batch.id,intake_id=case.id,topic=topic,tier=tier,recommended=t.predicted,confidence=t.confidence,facts_version=case.facts_version,facts_snapshot=case.facts))
    return finish(db,user,'抽检建批',batch)
def determine(db,id,data,user):
    sample=get(db,AuditSample,id,True);batch=get(db,AuditBatch,sample.batch_id,True)
    reject(batch.status!=AuditBatchState.open.value,'批次已封批，不能再核定')
    case=get(db,Intake,sample.intake_id,True)
    reject(case.facts_version!=sample.facts_version,'事实已更正，该样本封批时记为缺样，无需核定')
    sample.determined=data.topic;sample.determined_by=user.username;sample.determined_at=now();sample.attempts+=1
    return finish(db,user,'盲核核定',sample)
def seal(db,id,user):
    batch=get(db,AuditBatch,id,True)
    reject(batch.status!=AuditBatchState.open.value,'批次已封批')
    samples=list(db.scalars(select(AuditSample).where(AuditSample.batch_id==id)))
    for s in samples:
        case=get(db,Intake,s.intake_id,True)
        if case.facts_version!=s.facts_version:s.missing=True
    pending=sum(1 for s in samples if not s.missing and s.determined is None)
    reject(pending,f'还有{pending}份样本未核定，复核未完成，暂不出成绩')
    strata=list(db.scalars(select(AuditStratum).where(AuditStratum.batch_id==id)))
    low=high=weight=0.0
    for st in strata:
        members=[s for s in samples if s.topic==st.topic and s.tier==st.tier]
        errors=sum(1 for s in members if not s.missing and s.determined!=s.recommended)
        lost=sum(1 for s in members if s.missing)
        low+=st.population*errors/st.sample_size;high+=st.population*(errors+lost)/st.sample_size;weight+=st.population
    batch.rate_low=low/weight;batch.rate_high=high/weight;batch.status=AuditBatchState.sealed.value;batch.sealed_at=now()
    return finish(db,user,'封批出分',batch)
def stale(batch,sample,case):
    if batch.status==AuditBatchState.sealed.value:return sample.missing
    return case.facts_version!=sample.facts_version
def sample_view(batch,sample,case):
    cut=stale(batch,sample,case)
    view={'id':sample.id,'intake_id':sample.intake_id,'code':case.code,'facts_snapshot':sample.facts_snapshot,'facts_version':sample.facts_version,'stale':cut,'missing':sample.missing,'determined':sample.determined,'determined_by':sample.determined_by,'attempts':sample.attempts}
    if batch.status==AuditBatchState.sealed.value or sample.determined is not None:
        view.update(topic=sample.topic,tier=sample.tier,recommended=sample.recommended,confidence=sample.confidence)
    return view
def progress(batch,samples,cases):
    cut=sum(1 for s in samples if stale(batch,s,cases[s.intake_id]))
    scored=sum(1 for s in samples if s.determined is not None and not stale(batch,s,cases[s.intake_id]))
    return {'total':len(samples),'stale':cut,'determined':scored}
def list_batches(db):
    out=[]
    for batch in db.scalars(select(AuditBatch).order_by(AuditBatch.id.desc())):
        samples=list(db.scalars(select(AuditSample).where(AuditSample.batch_id==batch.id)))
        cases={c.id:c for c in db.scalars(select(Intake).where(Intake.id.in_([s.intake_id for s in samples])))} if samples else {}
        out.append(dump(batch)|progress(batch,samples,cases))
    return out
def detail(db,id):
    batch=get(db,AuditBatch,id)
    samples=list(db.scalars(select(AuditSample).where(AuditSample.batch_id==id).order_by(AuditSample.id)))
    cases={c.id:c for c in db.scalars(select(Intake).where(Intake.id.in_([s.intake_id for s in samples])))} if samples else {}
    view=dump(batch)|progress(batch,samples,cases)
    view['samples']=[sample_view(batch,s,cases[s.intake_id]) for s in samples]
    if batch.status==AuditBatchState.sealed.value:
        view['strata']=[stratum_view(st,samples) for st in db.scalars(select(AuditStratum).where(AuditStratum.batch_id==id).order_by(AuditStratum.id))]
    return view
def stratum_view(st,samples):
    members=[s for s in samples if s.topic==st.topic and s.tier==st.tier]
    errors=sum(1 for s in members if not s.missing and s.determined!=s.recommended)
    lost=sum(1 for s in members if s.missing)
    return {'topic':st.topic,'tier':st.tier,'population':st.population,'sample_size':st.sample_size,'errors':errors,'missing':lost,'rate_low':errors/st.sample_size,'rate_high':(errors+lost)/st.sample_size}
