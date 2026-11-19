from sqlalchemy import select,func
from .models import Intake,Referral,ServiceLog,Closure,Agency
from .common import get,reject,finish,lock_referral,active_referral
from .intake_service import authorized

def log_service(db,data,user):
    ref=lock_referral(db,data.referral_id)
    reject(ref.status!='accepted','机构尚未受理，不能登记服务工时')
    reject(not authorized(db,ref.intake_id),'授权已撤回，不能继续登记服务')
    row=ServiceLog(**data.model_dump());db.add(row);db.flush();return finish(db,user,'登记实际服务时长',row)
def close(db,data,user):
    case=get(db,Intake,data.intake_id,True);ref=active_referral(db,case.id)
    reject(case.status=='closed' or ref is None or ref.status!='accepted','仅已受理且未销案卷宗可以销案')
    get(db,Referral,ref.id,True);agency=get(db,Agency,ref.agency_id,True)
    reject(not authorized(db,case.id),'授权无效，先处理授权或中止承接')
    minutes=db.scalar(select(func.coalesce(func.sum(ServiceLog.minutes),0)).where(ServiceLog.referral_id==ref.id))
    reject(minutes<=0,'没有实际服务工时，不能销案')
    row=Closure(intake_id=case.id,referral_id=ref.id,satisfaction=data.satisfaction,followup=data.followup,total_minutes=minutes)
    db.add(row);ref.status='completed';case.status='closed';agency.active_count-=1;db.flush();return finish(db,user,'回访销案并释放容量',row)
