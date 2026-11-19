import unicodedata
from sqlalchemy import select
from .models import Party,CaseParty,ConflictCheck,Agency,Referral
from .common import get,reject,finish,editable,ACTIVE

def normalize(name):return ''.join(unicodedata.normalize('NFKC',name).casefold().split())
def party(db,data,user):
    editable(db,data.intake_id);name=normalize(data.name);reject(len(name)<2,'归一化当事人名称过短')
    p=db.scalar(select(Party).where(Party.normalized==name))
    if not p:p=Party(name=data.name.strip(),normalized=name);db.add(p);db.flush()
    opposite=db.scalar(select(CaseParty).where(CaseParty.intake_id==data.intake_id,CaseParty.side!=data.side,CaseParty.party_id==p.id))
    reject(opposite is not None,'双方不能是同一当事人')
    row=db.scalar(select(CaseParty).where(CaseParty.intake_id==data.intake_id,CaseParty.side==data.side))
    if row:row.party_id=p.id
    else:row=CaseParty(intake_id=data.intake_id,side=data.side,party_id=p.id);db.add(row);db.flush()
    return finish(db,user,'关联当事人更正',row)
def conflict(db,intake_id,agency_id):
    parties={r.side:r.party_id for r in db.scalars(select(CaseParty).where(CaseParty.intake_id==intake_id))}
    if set(parties)!=set(['client','opponent']):return True,'需补齐来访方与相对方'
    refs=list(db.scalars(select(Referral).where(Referral.agency_id==agency_id,Referral.intake_id!=intake_id,Referral.status.in_(ACTIVE))))
    for ref in refs:
        sides={r.side:r.party_id for r in db.scalars(select(CaseParty).where(CaseParty.intake_id==ref.intake_id))}
        if parties['client']==sides.get('opponent') or parties['opponent']==sides.get('client'):return True,'机构已承接对立当事人，改选其它机构'
    return False,'双方对照通过；转介时再次核验'
def check(db,data,user):
    from .models import Intake
    get(db,Intake,data.intake_id,True);get(db,Agency,data.agency_id,True)
    blocked,reason=conflict(db,data.intake_id,data.agency_id);row=ConflictCheck(**data.model_dump(),blocked=blocked,reason=reason);db.add(row);db.flush();return finish(db,user,'机构利益冲突核验',row)
