from datetime import datetime,timezone
from sqlalchemy import Integer,String,Float,ForeignKey,UniqueConstraint,CheckConstraint,JSON,DateTime,Boolean,Text
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
from .constants import IntakeState,ReferralState
def now():return datetime.now(timezone.utc)
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    username:Mapped[str]=mapped_column(String(40),unique=True)
    password:Mapped[str]=mapped_column(String(128))
    role:Mapped[str]=mapped_column(String(20))
class Intake(Base):
    __tablename__='intakes'
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    alias:Mapped[str]=mapped_column(String(60))
    facts:Mapped[str]=mapped_column(Text)
    facts_version:Mapped[int]=mapped_column(Integer,default=1)
    status:Mapped[str]=mapped_column(String(20),default=IntakeState.open.value)
class Consent(Base):
    __tablename__='consents'
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'),unique=True)
    authorized:Mapped[bool]=mapped_column(Boolean,default=False)
    basis:Mapped[str]=mapped_column(String(200),default='')
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Party(Base):
    __tablename__='parties'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(100))
    normalized:Mapped[str]=mapped_column(String(100),unique=True)
class CaseParty(Base):
    __tablename__='case_parties'
    __table_args__=(UniqueConstraint('intake_id','side'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'))
    party_id:Mapped[int]=mapped_column(ForeignKey('parties.id'))
    side:Mapped[str]=mapped_column(String(20))
class ConflictCheck(Base):
    __tablename__='conflict_checks'
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'))
    agency_id:Mapped[int]=mapped_column(ForeignKey('agencies.id'))
    blocked:Mapped[bool]=mapped_column(Boolean)
    reason:Mapped[str]=mapped_column(String(200))
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Triage(Base):
    __tablename__='triages'
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'))
    facts_version:Mapped[int]=mapped_column(Integer)
    status:Mapped[str]=mapped_column(String(20),default='queued')
    predicted:Mapped[str|None]=mapped_column(String(20),nullable=True)
    confidence:Mapped[float|None]=mapped_column(Float,nullable=True)
    approved:Mapped[str|None]=mapped_column(String(20),nullable=True)
    manual_required:Mapped[bool]=mapped_column(Boolean,default=True)
    review_note:Mapped[str]=mapped_column(String(200),default='')
    metrics:Mapped[dict]=mapped_column(JSON,default=dict)
    error:Mapped[str]=mapped_column(String(200),default='')
class Requirement(Base):
    __tablename__='requirements'
    __table_args__=(UniqueConstraint('topic','code'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    topic:Mapped[str]=mapped_column(String(20))
    code:Mapped[str]=mapped_column(String(40))
    title:Mapped[str]=mapped_column(String(80))
class Document(Base):
    __tablename__='documents'
    __table_args__=(UniqueConstraint('intake_id','requirement_id'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'))
    requirement_id:Mapped[int]=mapped_column(ForeignKey('requirements.id'))
    reference:Mapped[str]=mapped_column(String(160))
    status:Mapped[str]=mapped_column(String(20),default='submitted')
    note:Mapped[str]=mapped_column(String(200),default='')
class Agency(Base):
    __tablename__='agencies'
    __table_args__=(CheckConstraint('capacity > 0'),CheckConstraint('active_count >= 0 AND active_count <= capacity'))
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    name:Mapped[str]=mapped_column(String(80))
    specialties:Mapped[str]=mapped_column(String(100))
    capacity:Mapped[int]=mapped_column(Integer)
    active_count:Mapped[int]=mapped_column(Integer,default=0)
class Referral(Base):
    __tablename__='referrals'
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'))
    agency_id:Mapped[int]=mapped_column(ForeignKey('agencies.id'))
    topic:Mapped[str]=mapped_column(String(20))
    status:Mapped[str]=mapped_column(String(20),default=ReferralState.pending.value)
    receipt:Mapped[str]=mapped_column(String(120),default='')
    note:Mapped[str]=mapped_column(String(200),default='')
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ServiceLog(Base):
    __tablename__='service_logs'
    __table_args__=(CheckConstraint('minutes > 0 AND minutes <= 480'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    referral_id:Mapped[int]=mapped_column(ForeignKey('referrals.id'))
    minutes:Mapped[int]=mapped_column(Integer)
    description:Mapped[str]=mapped_column(String(200))
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Closure(Base):
    __tablename__='closures'
    id:Mapped[int]=mapped_column(primary_key=True)
    intake_id:Mapped[int]=mapped_column(ForeignKey('intakes.id'),unique=True)
    referral_id:Mapped[int]=mapped_column(ForeignKey('referrals.id'),unique=True)
    satisfaction:Mapped[int]=mapped_column(Integer)
    followup:Mapped[str]=mapped_column(String(200))
    total_minutes:Mapped[int]=mapped_column(Integer)
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Audit(Base):
    __tablename__='audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(40))
    action:Mapped[str]=mapped_column(String(100))
    detail:Mapped[str]=mapped_column(String(300))
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
