from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator

from core.events import AgentID, EventType


SCHEMA_VERSION = "1.0"


# ── Payload models ────────────────────────────────────────

class MetricPayload(BaseModel):
    service: str
    metric:  str
    value:   float
    unit:    str
    host:    str


class AnomalyPayload(BaseModel):
    service:         str
    metric:          str
    current_value:   float
    baseline_mean:   float
    baseline_std:    float
    z_score:         float
    severity:        str
    window_seconds:  int


class DiagnosisPayload(BaseModel):
    root_cause:          str
    confidence:          float
    affected:            list[str]
    similar_past:        list[str] = []
    evidence:            list[str] = []
    recommended_actions: list[str] = []


class PlanStep(BaseModel):
    order:       int
    action_type: str
    target:      str
    params:      dict[str, Any] = {}
    risk:        float
    compensate:  dict[str, Any] = {}


class RemedPlan(BaseModel):
    plan_id:    str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    label:      str
    steps:      list[PlanStep]
    risk_score: float
    rationale:  str


class PlanPayload(BaseModel):
    plans:        list[RemedPlan]
    auto_approve: bool
    uncertain:    bool = False


class ActionPayload(BaseModel):
    plan:        RemedPlan
    approved_by: str


class StepResultPayload(BaseModel):
    plan_id: str
    step:    PlanStep
    success: bool
    output:  str = ""
    error:   str = ""


class IncidentDonePayload(BaseModel):
    resolved:           bool
    rolled_back:        bool
    steps_executed:     int
    steps_rolled_back:  int
    duration_seconds:   float


class ApprovalReqPayload(BaseModel):
    plan:       RemedPlan
    reason:     str
    expires_at: datetime


class ApprovalRespPayload(BaseModel):
    plan_id:  str
    approved: bool
    approver: str
    note:     str = ""


class ErrorPayload(BaseModel):
    code:    str
    message: str
    detail:  str = ""


PAYLOAD_REGISTRY: dict[EventType, type[BaseModel]] = {
    EventType.METRIC:        MetricPayload,
    EventType.ANOMALY:       AnomalyPayload,
    EventType.DIAGNOSIS:     DiagnosisPayload,
    EventType.PLAN:          PlanPayload,
    EventType.ACTION:        ActionPayload,
    EventType.STEP_RESULT:   StepResultPayload,
    EventType.INCIDENT_DONE: IncidentDonePayload,
    EventType.APPROVAL_REQ:  ApprovalReqPayload,
    EventType.APPROVAL_RESP: ApprovalRespPayload,
    EventType.ERROR:         ErrorPayload,
}


# ── Envelope ──────────────────────────────────────────────

class CorvusEnvelope(BaseModel):
    schema_version: str      = SCHEMA_VERSION
    id:             str      = Field(default_factory=lambda: str(uuid.uuid4()))
    type:           EventType
    source:         AgentID
    target:         AgentID
    incident_id:    str
    payload:        dict[str, Any]
    ts:             datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace:          list[str] = []
    forwarded_from: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "CorvusEnvelope":
        model_cls = PAYLOAD_REGISTRY.get(self.type)
        if model_cls is None:
            raise ValueError(f"No payload model for EventType.{self.type}")
        model_cls(**self.payload)
        return self

    def typed_payload(self) -> BaseModel:
        return PAYLOAD_REGISTRY[self.type](**self.payload)

    def append_trace(self, agent: AgentID, step: str) -> "CorvusEnvelope":
        return self.model_copy(update={
            "trace": self.trace + [f"[{agent}] {step}"]
        })

    def forward_to(self, target: AgentID, source: AgentID) -> "CorvusEnvelope":
        return self.model_copy(update={
            "id":             str(uuid.uuid4()),
            "source":         source,
            "target":         target,
            "ts":             datetime.now(timezone.utc),
            "forwarded_from": self.id,
        })

    def to_kafka_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_bytes(cls, data: bytes) -> "CorvusEnvelope":
        return cls.model_validate_json(data.decode("utf-8"))
