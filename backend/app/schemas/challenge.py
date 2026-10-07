"""Challenge / KPI / suggestion schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KpiIn(BaseModel):
    name: str
    description: str = ""
    baseline: str = ""
    target: str = ""
    unit: str = ""
    measurement_method: str = ""
    evidence_source: str = ""
    success_threshold: str = ""
    direction: str = "reduce"


class ChallengeIn(BaseModel):
    title: str = ""
    department: str = ""
    problem_category: str = ""
    problem_statement: str = ""
    current_situation: str = ""
    affected_population: str = ""
    existing_process: str = ""
    current_limitations: str = ""
    expected_outcome: str = ""
    geographic_scope: str = ""
    constraints: str = ""
    priority: str = "MEDIUM"
    budget_min: float = 0
    budget_max: float = 0
    requirements: dict = {}
    pilot_criteria: dict = {}
    data_policy: dict = {}
    ip_policy: dict = {}
    cybersecurity: dict = {}
    risks: list = []


class ChallengeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    department: str
    problem_category: str
    problem_statement: str
    current_situation: str
    affected_population: str
    existing_process: str
    current_limitations: str
    expected_outcome: str
    geographic_scope: str
    constraints: str
    priority: str
    status: str
    budget_min: float
    budget_max: float
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None
    requirements: dict = {}
    pilot_criteria: dict = {}
    data_policy: dict = {}
    ip_policy: dict = {}
    cybersecurity: dict = {}
    risks: list = []


class SuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    challenge_id: str
    suggestion_type: str
    category: str
    text: str
    rationale: str
    confidence: float
    extra: dict = {}
    status: str
    edited_text: str | None = None
