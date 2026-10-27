"""Generation request, plan, and status schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class GenerationCreate(BaseModel):
    project_id: uuid.UUID
    quality_mode: Optional[str] = None
    allow_paid_apis: bool = False
    max_spend: Optional[float] = None


class GenerationPlanResponse(BaseModel):
    project_id: uuid.UUID
    target_duration: int
    scene_count: int
    estimated_cost: float
    selected_providers: Dict[str, str]
    quality_mode: str
    scenes: List[Dict[str, Any]]


class GenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    current_step: Optional[str] = None
    progress_percent: float
    total_scenes: int
    completed_scenes: int
    failed_scenes: int
    error_message: Optional[str] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    output_path: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class JobStatusUpdate(BaseModel):
    job_id: str
    status: str
    progress: float
    step: str
    scene_number: Optional[int] = None
    total_scenes: Optional[int] = None
    error: Optional[str] = None
    output_path: Optional[str] = None
