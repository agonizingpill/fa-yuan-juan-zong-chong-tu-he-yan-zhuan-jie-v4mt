from enum import StrEnum
class Role(StrEnum):
    operator='operator'
    supervisor='supervisor'
    viewer='viewer'
class IntakeState(StrEnum):
    open='open'
    referred='referred'
    accepted='accepted'
    closed='closed'
class Topic(StrEnum):
    labor='labor'
    housing='housing'
    consumer='consumer'
class ReferralState(StrEnum):
    pending='pending'
    accepted='accepted'
    withdrawn='withdrawn'
    completed='completed'
