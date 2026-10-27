"""Generation job scheduling, execution plan preview, and status API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.generation import Generation, GenerationStatus
from backend.models.project import Project
from backend.models.scene import Scene
from backend.models.user import User
from backend.schemas.generation import (
    GenerationCreate,
    GenerationPlanResponse,
    GenerationResponse,
)
from backend.workers.pipeline_tasks import generate_full_video_pipeline

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=GenerationResponse, status_code=status.HTTP_201_CREATED)
async def create_generation_job(
    data: GenerationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new generation job and triggers background pipeline execution."""
    project = await db.get(Project, data.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count planned scenes
    scenes_stmt = select(Scene).where(Scene.project_id == project.id).order_by(Scene.scene_number)
    scenes = (await db.execute(scenes_stmt)).scalars().all()

    generation = Generation(
        project_id=project.id,
        user_id=current_user.id,
        status=GenerationStatus.QUEUED,
        total_scenes=len(scenes) or max(3, round(project.target_duration / 6)),
        completed_scenes=0,
        failed_scenes=0,
        current_step="Queued in production pipeline",
        progress_percent=0.0,
        started_at=datetime.utcnow(),
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # Launch generation pipeline in background (or via Celery worker)
    background_tasks.add_task(
        generate_full_video_pipeline,
        project_id=str(project.id),
        generation_id=str(generation.id),
        quality_mode=data.quality_mode or project.quality_mode or "balanced",
    )

    return generation


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation_status(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch current real-time job status, progress percentage, and step details."""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return gen


@router.get("/{generation_id}/plan", response_model=GenerationPlanResponse)
async def get_generation_plan(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Previews the generation plan before running expensive generation tasks."""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation job not found")

    project = await db.get(Project, gen.project_id)
    scenes_stmt = select(Scene).where(Scene.project_id == project.id).order_by(Scene.scene_number)
    scenes = (await db.execute(scenes_stmt)).scalars().all()

    # Determine recommended providers for this quality mode
    providers = {
        "script": "Gemini / Groq / Local LLM",
        "images": "Local Engine / ComfyUI / HF",
        "video": "Local ComfyUI / Fal / Replicate",
        "voice": "Local System TTS / ElevenLabs",
    }

    return GenerationPlanResponse(
        project_id=project.id,
        target_duration=project.target_duration,
        scene_count=len(scenes),
        estimated_cost=0.0 if project.quality_mode == "local" else 0.05,
        selected_providers=providers,
        quality_mode=project.quality_mode,
        scenes=[{"scene_number": s.scene_number, "title": s.title, "duration": s.duration_seconds} for s in scenes],
    )


@router.post("/{generation_id}/cancel")
async def cancel_generation_job(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancels a queued or running generation job."""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation job not found")

    gen.status = GenerationStatus.CANCELLED
    gen.current_step = "Job cancelled by user"
    await db.commit()
    return {"status": "cancelled"}


@router.post("/{generation_id}/resume", response_model=GenerationResponse)
async def resume_generation_job(
    generation_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resumes an interrupted or failed generation without losing already generated scenes."""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation job not found")

    project = await db.get(Project, gen.project_id)
    gen.status = GenerationStatus.QUEUED
    gen.current_step = "Resuming generation pipeline..."
    gen.error_message = None
    await db.commit()
    await db.refresh(gen)

    background_tasks.add_task(
        generate_full_video_pipeline,
        project_id=str(project.id),
        generation_id=str(gen.id),
        quality_mode=project.quality_mode or "balanced",
    )

    return gen
