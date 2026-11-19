from pydantic import BaseModel,Field
class Login(BaseModel):
    username:str
    password:str
class IntakeInput(BaseModel):
    code:str=Field(min_length=3,max_length=40)
    alias:str=Field(min_length=2,max_length=60)
    facts:str=Field(min_length=8,max_length=3000)
class FactsInput(BaseModel):
    facts:str=Field(min_length=8,max_length=3000)
class ConsentInput(BaseModel):
    authorized:bool
    basis:str=Field(min_length=3,max_length=200)
class PartyInput(BaseModel):
    intake_id:int
    side:str=Field(pattern='^(client|opponent)$')
    name:str=Field(min_length=2,max_length=100)
class CheckInput(BaseModel):
    intake_id:int
    agency_id:int
class TriageInput(BaseModel):
    intake_id:int
class ReviewInput(BaseModel):
    topic:str=Field(pattern='^(labor|housing|consumer)$')
    note:str=Field(min_length=3,max_length=200)
class DocumentInput(BaseModel):
    intake_id:int
    requirement_id:int
    reference:str=Field(min_length=4,max_length=160)
class DocumentReview(BaseModel):
    accepted:bool
    note:str=Field(min_length=3,max_length=200)
class AgencyInput(BaseModel):
    code:str=Field(min_length=2,max_length=40)
    name:str=Field(min_length=2,max_length=80)
    specialties:list[str]=Field(min_length=1,max_length=3)
    capacity:int=Field(ge=1,le=100)
class ReferralInput(BaseModel):
    intake_id:int
    agency_id:int
class ReceiptInput(BaseModel):
    receipt:str=Field(min_length=4,max_length=120)
class WithdrawInput(BaseModel):
    note:str=Field(min_length=3,max_length=200)
class ServiceInput(BaseModel):
    referral_id:int
    minutes:int=Field(ge=1,le=480)
    description:str=Field(min_length=4,max_length=200)
class ClosureInput(BaseModel):
    intake_id:int
    satisfaction:int=Field(ge=1,le=5)
    followup:str=Field(min_length=4,max_length=200)
