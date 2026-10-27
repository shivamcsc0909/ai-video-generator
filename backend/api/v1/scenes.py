"""Scene inspection and granular regeneration API endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.project import Project
from backend.models.scene import Scene
from backend.models.user import User
from backend.schemas.scene import SceneResponse, SceneUpdate

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a single scene."""
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    project = await db.get(Project, scene.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.put("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: uuid.UUID,
    data: SceneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit scene prompts, duration, or visual descriptions."""
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    project = await db.get(Project, scene.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scene not found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(scene, field, val)

    await db.commit()
    await db.refresh(scene)
    return scene


@router.post("/{scene_id}/regenerate", response_model=SceneResponse)
async def regenerate_single_scene(
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerates only this single scene without re-rendering the entire video."""
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    project = await db.get(Project, scene.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scene not found")

    from backend.providers.base.provider_interface import GenerationRequest
    from backend.services.provider_router.router import ProviderRouter

    router_svc = ProviderRouter(db)
    req = GenerationRequest(
        prompt=scene.video_prompt or scene.image_prompt,
        negative_prompt=scene.negative_prompt,
        duration_seconds=scene.duration_seconds,
        aspect_ratio=project.aspect_ratio,
    )

    scene.status = "generating"
    scene.retry_count += 1
    await db.commit()

    res = await router_svc.route_video_generation(
        request=req,
        quality_mode=project.quality_mode or "balanced",
    )

    if res.success:
        scene.status = "completed"
        scene.video_path = res.output_path or res.output_url
        scene.provider_used = res.model_used
        scene.error_message = None
    else:
        scene.status = "failed"
        scene.error_message = res.error_message

    await db.commit()
    await db.refresh(scene)
    return scene
