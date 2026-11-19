import hmac
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .database import session
from .models import *
from .schemas import *
from .auth import current,editor,supervisor,issue,password_hash
from .common import dump
from . import intake_service as intake,conflict_service as conflict,triage_service as triage,document_service as document,referral_service as referral,closure_service as closure
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,db=Depends(session)):
    row=db.scalar(select(User).where(User.username==data.username))
    if not row or not hmac.compare_digest(row.password,password_hash(data.password)):raise HTTPException(401,'账号或密码错误')
    return {'token':issue(row),'username':row.username,'role':row.role}
@router.get('/workspace')
def workspace(db=Depends(session),user=Depends(current)):
    return {m.__tablename__:[dump(v) for v in db.scalars(select(m).order_by(m.id))] for m in [Intake,Consent,Party,CaseParty,ConflictCheck,Triage,Requirement,Document,Agency,Referral,ServiceLog,Closure]}
@router.post('/intakes')
def create(data:IntakeInput,db=Depends(session),user=Depends(editor)):return intake.create(db,data,user)
@router.patch('/intakes/{id}/facts')
def facts(id:int,data:FactsInput,db=Depends(session),user=Depends(editor)):return intake.revise(db,id,data,user)
@router.post('/intakes/{id}/consent')
def consent(id:int,data:ConsentInput,db=Depends(session),user=Depends(editor)):return intake.consent(db,id,data,user)
@router.post('/parties')
def party(data:PartyInput,db=Depends(session),user=Depends(editor)):return conflict.party(db,data,user)
@router.post('/conflict-checks')
def check(data:CheckInput,db=Depends(session),user=Depends(editor)):return conflict.check(db,data,user)
@router.post('/triages')
def enqueue(data:TriageInput,db=Depends(session),user=Depends(editor)):return triage.enqueue(db,data,user)
@router.post('/triages/{id}/review')
def review(id:int,data:ReviewInput,db=Depends(session),user=Depends(supervisor)):return triage.review(db,id,data,user)
@router.post('/documents')
def submit(data:DocumentInput,db=Depends(session),user=Depends(editor)):return document.submit(db,data,user)
@router.post('/documents/{id}/verify')
def verify(id:int,data:DocumentReview,db=Depends(session),user=Depends(supervisor)):return document.verify(db,id,data,user)
@router.post('/agencies')
def agency(data:AgencyInput,db=Depends(session),user=Depends(supervisor)):return referral.agency(db,data,user)
@router.post('/referrals')
def refer(data:ReferralInput,db=Depends(session),user=Depends(supervisor)):return referral.refer(db,data,user)
@router.post('/referrals/{id}/accept')
def accept(id:int,data:ReceiptInput,db=Depends(session),user=Depends(supervisor)):return referral.accept(db,id,data,user)
@router.post('/referrals/{id}/withdraw')
def withdraw(id:int,data:WithdrawInput,db=Depends(session),user=Depends(supervisor)):return referral.withdraw(db,id,data,user)
@router.post('/service-logs')
def service(data:ServiceInput,db=Depends(session),user=Depends(editor)):return closure.log_service(db,data,user)
@router.post('/closures')
def close(data:ClosureInput,db=Depends(session),user=Depends(supervisor)):return closure.close(db,data,user)
@router.get('/audit')
def audits(db=Depends(session),user=Depends(supervisor)):return [dump(v) for v in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100))]
