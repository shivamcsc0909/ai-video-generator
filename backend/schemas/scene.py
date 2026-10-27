"""Scene schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class SceneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_seconds: Optional[float] = None
    shot_type: Optional[str] = None
    camera_movement: Optional[str] = None
    environment: Optional[str] = None
    lighting: Optional[str] = None
    voice_over: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    music_mood: Optional[str] = None
    sfx_description: Optional[str] = None
    transition_in: Optional[str] = None
    transition_out: Optional[str] = None
    continuity_notes: Optional[str] = None


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    generation_id: Optional[uuid.UUID] = None
    scene_number: int
    title: str
    description: Optional[str] = None
    duration_seconds: float
    status: str
    shot_type: Optional[str] = None
    camera_movement: Optional[str] = None
    environment: Optional[str] = None
    lighting: Optional[str] = None
    voice_over: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    music_mood: Optional[str] = None
    sfx_description: Optional[str] = None
    transition_in: Optional[str] = None
    transition_out: Optional[str] = None
    continuity_notes: Optional[str] = None
    provider_used: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    retry_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StoryboardResponse(BaseModel):
    project_id: uuid.UUID
    title: str
    script: str
    voice_script: str
    total_duration: float
    scene_bible: Dict[str, Any]
    scenes: List[SceneResponse]
