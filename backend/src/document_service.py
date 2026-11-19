from sqlalchemy import select
from .models import Document,Requirement,Intake
from .common import get,reject,finish,editable
from .triage_service import latest

def submit(db,data,user):
    editable(db,data.intake_id);requirement=get(db,Requirement,data.requirement_id)
    triage=latest(db,data.intake_id);reject(not triage or triage.approved!=requirement.topic,'材料类型与当前复核主题不符')
    row=db.scalar(select(Document).where(Document.intake_id==data.intake_id,Document.requirement_id==data.requirement_id))
    if row:row.reference=data.reference;row.status='submitted';row.note=''
    else:row=Document(**data.model_dump());db.add(row);db.flush()
    return finish(db,user,'提交脱敏材料索引',row)
def verify(db,id,data,user):
    initial=get(db,Document,id);editable(db,initial.intake_id);row=get(db,Document,id,True)
    reject(row.status!='submitted','仅待核验材料可以复核')
    row.status='verified' if data.accepted else 'rejected';row.note=data.note;return finish(db,user,'材料核验补正',row)
def missing(db,id,topic):
    required=list(db.scalars(select(Requirement).where(Requirement.topic==topic)))
    verified=set(db.scalars(select(Document.requirement_id).where(Document.intake_id==id,Document.status=='verified')))
    return [r.title for r in required if r.id not in verified]
