from sqlalchemy import select
from .models import Intake,Consent,Agency,now
from .common import get,reject,finish,active_referral,editable

def create(db,data,user):
    reject(db.scalar(select(Intake).where(Intake.code==data.code)) is not None,'收件编号已存在')
    row=Intake(**data.model_dump());db.add(row);db.flush();db.add(Consent(intake_id=row.id,authorized=False,basis='尚未取得转介授权'));return finish(db,user,'来访建卷',row)
def revise(db,id,data,user):
    row=editable(db,id);row.facts=data.facts;row.facts_version+=1;return finish(db,user,'事实更正并更新版本',row)
def consent(db,id,data,user):
    case=get(db,Intake,id,True);row=db.scalar(select(Consent).where(Consent.intake_id==id))
    reject(case.status=='closed','销案卷宗只读')
    ref=active_referral(db,id)
    if not data.authorized and ref is not None:
        agency=get(db,Agency,ref.agency_id,True);agency.active_count-=1;ref.status='withdrawn';ref.note='来访人撤回授权，自动退回';case.status='open'
    row.authorized=data.authorized;row.basis=data.basis;row.at=now();return finish(db,user,'授权更新',row)
def authorized(db,id):
    row=db.scalar(select(Consent).where(Consent.intake_id==id))
    return row is not None and row.authorized
