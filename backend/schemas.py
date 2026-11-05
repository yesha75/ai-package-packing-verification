"""Models shared across API and internal pipeline."""
from typing import Literal
from pydantic import BaseModel, Field


class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2


class Checklist(BaseModel):
    id: str
    name: str
    items: dict[str, int]  # expected item quantities


class VerificationResult(BaseModel):
    status: Literal["Pass", "Needs Review"]
    reasons: list[str]
    detected_counts: dict[str, int]
    missing: dict[str, int]
    unexpected: dict[str, int]
    excess: dict[str, int]
    uncertain: bool


class InspectionResponse(VerificationResult):
    id: str
    checklist_id: str
    filename: str
    created_at: str
    processing_ms: float
    detections: list[Detection]
    annotated_image_url: str
