"""Pilot / milestone / evidence / validation / decision schemas."""
from pydantic import BaseModel


class PilotIn(BaseModel):
    name: str
    startup_id: str
    challenge_id: str | None = None
    duration_weeks: int = 12
    budget: float = 0
    objectives: str = ""
    sites: int = 1
    target_users: str = ""
    geographic_scope: str = ""


class PilotPatch(BaseModel):
    name: str | None = None
    duration_weeks: int | None = None
    budget: float | None = None
    objectives: str | None = None
    expected_outcome: str | None = None
    sites: int | None = None
    target_users: str | None = None
    geographic_scope: str | None = None
    success_criteria: str | None = None
    payment_conditions: str | None = None
    baseline: dict | None = None
    data_ip: dict | None = None
    cybersecurity: dict | None = None


class MilestoneIn(BaseModel):
    name: str
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    deliverable: str = ""
    kpi_dependency: str = ""
    payment_percentage: float = 0


class MilestoneStatus(BaseModel):
    status: str | None = None
    payment_status: str | None = None


class KpiObservation(BaseModel):
    claimed_value: str | None = None
    observed_value: str | None = None
    status: str | None = None
    note: str = ""


class EvaluationIn(BaseModel):
    scores: dict  # criterion_key -> {score, justification}
    recommendation: str
    final_comments: str = ""


class CoiIn(BaseModel):
    status: str  # NO_CONFLICT | POTENTIAL_CONFLICT | CONFIRMED_CONFLICT
    conflict_type: str = ""
    description: str = ""


class ValidationFindingIn(BaseModel):
    kpi_id: str | None = None
    claimed: str = ""
    observed: str = ""
    validated_value: str = ""
    target: str = ""
    finding: str
    explanation: str = ""


class ValidationReportIn(BaseModel):
    summary: str
    overall_finding: str
    validated_kpis: dict = {}


class GovernmentDecisionIn(BaseModel):
    decision: str  # SCALE | RE_PILOT | REJECT | INSUFFICIENT_EVIDENCE
    reason: str
    override: bool = False


class PilotKpiPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    baseline: str | None = None
    target: str | None = None
    unit: str | None = None
    measurement_method: str | None = None
    evidence_source: str | None = None
    success_threshold: str | None = None
    direction: str | None = None
    status: str | None = None
    observed_value: str | None = None
    claimed_value: str | None = None
    progress_notes: list | None = None


class ScalePlanIn(BaseModel):
    scale_scope: dict = {}
    new_kpis: list = []
    support_requirements: list = []
