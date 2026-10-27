"""Voice Studio, language support, and audio preview endpoints."""

from __future__ import annotations

import os
import tempfile
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.services.provider_router.router import ProviderRouter

logger = structlog.get_logger(__name__)
router = APIRouter()

SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "accents": ["American", "British", "Indian", "Australian"]},
    {"code": "hi", "name": "Hindi (हिंदी)", "accents": ["Standard", "Modern"]},
    {"code": "hinglish", "name": "Hinglish", "accents": ["Urban Indian"]},
    {"code": "es", "name": "Spanish (Español)", "accents": ["Castilian", "Latin American"]},
    {"code": "fr", "name": "French (Français)", "accents": ["Parisian", "Canadian"]},
    {"code": "de", "name": "German (Deutsch)", "accents": ["Standard"]},
    {"code": "ja", "name": "Japanese (日本語)", "accents": ["Tokyo"]},
    {"code": "zh", "name": "Chinese (Mandarin)", "accents": ["Mainland", "Taiwanese"]},
    {"code": "ar", "name": "Arabic (العربية)", "accents": ["Standard Modern"]},
    {"code": "pt", "name": "Portuguese", "accents": ["Brazilian", "European"]},
]

PRESET_VOICES = [
    {"id": "Samantha", "name": "Samantha (Natural American Female)", "gender": "female", "language": "en", "style": "Commercial"},
    {"id": "Daniel", "name": "Daniel (British Male)", "gender": "male", "language": "en", "style": "Documentary"},
    {"id": "Rishi", "name": "Rishi (Indian English Male)", "gender": "male", "language": "en", "style": "Explainer"},
    {"id": "Lekha", "name": "Lekha (Hindi Female)", "gender": "female", "language": "hi", "style": "Warm / Expressive"},
    {"id": "Monica", "name": "Monica (Spanish Female)", "gender": "female", "language": "es", "style": "Energetic"},
]


@router.get("/languages")
async def list_supported_languages():
    """List supported voice languages and accents."""
    return SUPPORTED_LANGUAGES


@router.get("/voices")
async def list_available_voices():
    """List available voice profiles and styles."""
    return PRESET_VOICES


@router.post("/preview")
async def preview_voice_synthesis(
    text: str = "Welcome to the Local AI Video Production Studio.",
    language: str = "en",
    speed: float = 1.0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synthesizes a short voice preview clip."""
    router_svc = ProviderRouter(db)
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_wav.close()

    voice_settings = {
        "language": language,
        "speed": speed,
    }

    res = await router_svc.route_tts(
        text=text,
        voice_settings=voice_settings,
        output_path=temp_wav.name,
        quality_mode="local",
    )

    if not res.success:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {res.error_message}")

    return {
        "success": True,
        "preview_path": res.output_path,
        "model_used": res.model_used,
    }
