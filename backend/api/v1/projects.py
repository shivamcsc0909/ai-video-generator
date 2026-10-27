"""Project lifecycle and storyboard generation API endpoints."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.project import Project, ProjectStatus, ProjectType
from backend.models.scene import Scene
from backend.models.user import User
from backend.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from backend.schemas.scene import StoryboardResponse
from backend.services.provider_router.router import ProviderRouter
from backend.services.storyboard.engine import StoryboardEngine

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all user projects."""
    count_stmt = select(func.count(Project.id)).where(Project.user_id == current_user.id)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    projects = res.scalars().all()
    return ProjectListResponse(items=projects, total=total)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new video production project."""
    try:
        p_type = ProjectType(data.project_type)
    except Exception:
        p_type = ProjectType.advertisement

    project = Project(
        user_id=current_user.id,
        name=data.name.strip(),
        description=data.description,
        project_type=p_type,
        status=ProjectStatus.draft,
        prompt=data.prompt.strip(),
        script=data.script,
        target_duration=data.target_duration,
        aspect_ratio=data.aspect_ratio,
        quality_mode=data.quality_mode,
        voice_language=data.voice_language,
        voice_accent=data.voice_accent,
        voice_name=data.voice_name,
        voice_emotion=data.voice_emotion,
        voice_speed=data.voice_speed,
        include_subtitles=data.include_subtitles,
        include_music=data.include_music,
        include_sfx=data.include_sfx,
        settings=data.settings or {},
        scene_bible={},
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project details."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update project settings or prompt."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(project, field, val)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project and related scenes."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/generate-storyboard", response_model=StoryboardResponse)
async def generate_project_storyboard(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate structured storyboard and scene breakdown using AI Storyboard Engine."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    router_svc = ProviderRouter(db)
    engine = StoryboardEngine(router_svc)

    storyboard = await engine.generate_storyboard(
        prompt=project.prompt,
        project_type=project.project_type.value if hasattr(project.project_type, "value") else str(project.project_type),
        target_duration=project.target_duration,
        aspect_ratio=project.aspect_ratio,
        voice_language=project.voice_language or "en",
    )

    # Clean old draft scenes for this project
    del_stmt = select(Scene).where(Scene.project_id == project.id)
    existing_scenes = (await db.execute(del_stmt)).scalars().all()
    for s in existing_scenes:
        await db.delete(s)

    created_scenes = []
    for sc in storyboard.scenes:
        scene_obj = Scene(
            project_id=project.id,
            scene_number=sc.scene_number,
            title=sc.title,
            description=sc.description,
            duration_seconds=sc.duration_seconds,
            shot_type=sc.shot_type,
            camera_movement=sc.camera_movement,
            environment=sc.environment,
            lighting=sc.lighting,
            voice_over=sc.voice_over,
            image_prompt=sc.image_prompt,
            video_prompt=sc.video_prompt,
            negative_prompt=sc.negative_prompt,
            music_mood=sc.music_mood,
            sfx_description=sc.sfx_description,
            transition_in=sc.transition_in,
            transition_out=sc.transition_out,
            continuity_notes=sc.continuity_notes,
            status="pending",
        )
        db.add(scene_obj)
        created_scenes.append(scene_obj)

    project.script = storyboard.script
    project.scene_bible = storyboard.scene_bible
    await db.commit()

    for s in created_scenes:
        await db.refresh(s)

    return StoryboardResponse(
        project_id=project.id,
        title=storyboard.title,
        script=storyboard.script,
        voice_script=storyboard.voice_script,
        total_duration=storyboard.total_duration,
        scene_bible=storyboard.scene_bible,
        scenes=created_scenes,
    )
