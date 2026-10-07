"""Shared API schemas."""
from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    message: str
    id: str | None = None
    errors: list[str] = []


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: str | None = None
    actor_id: str
    actor_name: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str | None = None
    old_value: dict | list | None = None
    new_value: dict | list | None = None
    reason: str | None = None
    metadata: dict | None = None
    correlation_id: str | None = None
