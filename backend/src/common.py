from fastapi import HTTPException
from sqlalchemy import select
from .models import Audit,Intake,Referral
ACTIVE=('pending','accepted')
def get(db,model,id,lock=False):
    stmt=select(model).where(model.id==id)
    if lock:stmt=stmt.with_for_update().execution_options(populate_existing=True)
    row=db.scalar(stmt)
    if not row:raise HTTPException(404,'卷宗或关联记录不存在')
    return row
def reject(condition,message):
    if condition:raise HTTPException(409,message)
def dump(row):return {c.name:getattr(row,c.name) for c in row.__table__.columns}
def finish(db,user,action,row):
    db.add(Audit(actor=user.username,action=action,detail=str(row.id)));db.commit();return dump(row)
def active_referral(db,id):return db.scalar(select(Referral).where(Referral.intake_id==id,Referral.status.in_(ACTIVE)))
def editable(db,id):
    case=get(db,Intake,id,True)
    reject(case.status=='closed','卷宗已销案，不能修改')
    reject(active_referral(db,id) is not None,'存在在途转介，请先撤回未受理转介')
    return case
def lock_referral(db,id):
    initial=get(db,Referral,id);get(db,Intake,initial.intake_id,True);return get(db,Referral,id,True)
