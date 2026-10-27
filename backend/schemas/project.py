"""Project request and response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_type: str = "advertisement"
    prompt: str = Field(..., min_length=5)
    script: Optional[str] = None
    target_duration: int = Field(60, ge=10, le=600)  # up to 10 min
    aspect_ratio: str = "16:9"                       # 16:9, 9:16, 1:1, 4:5
    quality_mode: str = "balanced"                   # local, balanced, quality, max_quality

    # Voice narration preferences
    voice_language: str = "en"
    voice_accent: Optional[str] = "American"
    voice_name: Optional[str] = "Samantha"
    voice_emotion: Optional[str] = "Confident"
    voice_speed: float = 1.0

    # Layer switches
    include_subtitles: bool = True
    include_music: bool = True
    include_sfx: bool = True

    settings: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    script: Optional[str] = None
    target_duration: Optional[int] = None
    aspect_ratio: Optional[str] = None
    quality_mode: Optional[str] = None
    voice_language: Optional[str] = None
    voice_accent: Optional[str] = None
    voice_name: Optional[str] = None
    voice_emotion: Optional[str] = None
    voice_speed: Optional[float] = None
    include_subtitles: Optional[bool] = None
    include_music: Optional[bool] = None
    include_sfx: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    scene_bible: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    project_type: str
    status: str
    prompt: str
    script: Optional[str] = None
    target_duration: int
    aspect_ratio: str
    quality_mode: str
    voice_language: Optional[str] = None
    voice_accent: Optional[str] = None
    voice_name: Optional[str] = None
    voice_emotion: Optional[str] = None
    voice_speed: float
    include_subtitles: bool
    include_music: bool
    include_sfx: bool
    output_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    scene_bible: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
