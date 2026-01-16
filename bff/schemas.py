from pydantic import BaseModel, Field, UUID4
from pydantic import ConfigDict
from typing import Optional
from enum import Enum


# --- Enums ---
class ReconStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class ActionType(str, Enum):
    APPROVE = "APPROVE"
    OVERRIDE = "OVERRIDE"


# --- Response Models (What the UI sees) ---
class ReasonCodeRead(BaseModel):
    reason_id: int
    code: str
    description: str
    is_functional: bool


class DifferenceRead(BaseModel):
    diff_id: UUID4
    field_name: str
    value_a: Optional[str]
    value_b: Optional[str]
    diff_type: str


class ReviewItem(BaseModel):
    """Represents a single row in the Review Queue"""

    attribution_id: UUID4
    confidence_score: float
    status: ReconStatus

    # Nested Relations
    difference: DifferenceRead
    current_reason: Optional[ReasonCodeRead]

    # Context (The full record data for UI display)
    source_a_ref_id: str
    source_b_ref_id: str

    model_config = ConfigDict(from_attributes=True)


# --- Request Models (What the User sends) ---
class ResolveRequest(BaseModel):
    attribution_id: UUID4
    action: ActionType  # 'APPROVE' or 'OVERRIDE'

    # Required only if overriding
    new_reason_code: Optional[str] = None
    comments: Optional[str] = Field(None, min_length=5)

    # User ID (In a real app, this comes from JWT Token)
    actor_id: str
