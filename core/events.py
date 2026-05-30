from enum import StrEnum


class EventType(StrEnum):
    METRIC        = "METRIC"
    ANOMALY       = "ANOMALY"
    DIAGNOSIS     = "DIAGNOSIS"
    PLAN          = "PLAN"
    ACTION        = "ACTION"
    STEP_RESULT   = "STEP_RESULT"
    INCIDENT_DONE = "INCIDENT_DONE"
    APPROVAL_REQ  = "APPROVAL_REQ"
    APPROVAL_RESP = "APPROVAL_RESP"
    ERROR         = "ERROR"


class AgentID(StrEnum):
    OBSERVER     = "observer"
    FORENSICS    = "forensics"
    EXECUTOR     = "executor"
    ORCHESTRATOR = "orchestrator"
    SYSTEM       = "system"
    HUMAN        = "human"
    BROADCAST    = "broadcast"


class AnomalySeverity(StrEnum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    DETECTING         = "DETECTING"
    DIAGNOSING        = "DIAGNOSING"
    PLANNING          = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING         = "EXECUTING"
    RESOLVED          = "RESOLVED"
    ROLLED_BACK       = "ROLLED_BACK"
    FAILED            = "FAILED"


class ActionType(StrEnum):
    RESTART_SERVICE   = "RESTART_SERVICE"
    SCALE_SERVICE     = "SCALE_SERVICE"
    REROUTE_TRAFFIC   = "REROUTE_TRAFFIC"
    FLUSH_CACHE       = "FLUSH_CACHE"
    RESET_CONNECTIONS = "RESET_CONNECTIONS"
    NOTIFY            = "NOTIFY"
