"""System diagnostics, hardware detection, model registry, and setup API."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.models.generation import Generation
from backend.models.model_registry import ModelRegistry
from backend.models.project import Project
from backend.services.credentials.encryption import CredentialEncryptionService
from backend.services.hardware.detector import detect_hardware

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def system_health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@router.get("/hardware")
async def get_hardware_info():
    """Detect Apple Silicon, GPU, unified memory, disk space, and media tools."""
    info = detect_hardware()
    return info.to_dict()


@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """System queue counts and project statistics."""
    total_projects = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    total_jobs = (await db.execute(select(func.count(Generation.id)))).scalar() or 0

    return {
        "total_projects": total_projects,
        "total_generations": total_jobs,
        "ffmpeg_status": "Available" if detect_hardware().ffmpeg_available else "Not detected in PATH",
        "comfyui_status": "Connected" if detect_hardware().comfyui_running else "Offline / Disconnected",
    }


@router.get("/models")
async def list_model_registry(db: AsyncSession = Depends(get_db)):
    """List registered AI models and capabilities."""
    stmt = select(ModelRegistry).order_by(ModelRegistry.model_name)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/generate-key-hint")
async def generate_encryption_key_helper():
    """Generates a secure Fernet encryption key hint for setup."""
    return {
        "generated_key": CredentialEncryptionService.generate_key(),
        "instructions": "Place this in your .env as ENCRYPTION_KEY or let the backend persist it automatically to ~/.videostudio_key",
    }
