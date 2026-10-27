"""Main FastAPI Application Entrypoint.

Provides:
- REST API v1 endpoints
- WebSocket real-time progress streaming
- Static file serving for generated renders & uploaded assets
- Startup initialization: DB schema creation, default admin user, provider registry seeding
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog
from sqlalchemy import select

from backend.api.v1.router import api_router
from backend.core.config import get_settings
from backend.core.database import AsyncSessionLocal, init_db
from backend.core.logging import RequestLoggingMiddleware, setup_logging
from backend.core.security import hash_password
from backend.core.websocket import manager as ws_manager
from backend.models.provider import Provider, ProviderAccount, ProviderType
from backend.models.user import User
from backend.services.hardware.detector import detect_hardware

setup_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()


async def seed_initial_data():
    """Seed database with default admin user and standard provider definitions."""
    async with AsyncSessionLocal() as db:
        # 1. Default local admin user
        res = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        admin = res.scalar_one_or_none()
        if not admin:
            admin_pwd = settings.ADMIN_PASSWORD or "admin123"
            admin = User(
                username=settings.ADMIN_USERNAME,
                email="admin@localhost",
                hashed_password=hash_password(admin_pwd),
                is_active=True,
                is_admin=True,
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            logger.info("default_admin_created", username=settings.ADMIN_USERNAME)

        # 2. Supported AI Providers seeding
        default_providers = [
            {
                "name": "google_gemini",
                "display_name": "Google Gemini",
                "provider_type": ProviderType.llm,
                "description": "Multimodal LLM for script writing, storyboarding, and prompt expansion.",
                "supports_local": False,
                "capabilities": ["text_generation"],
            },
            {
                "name": "groq",
                "display_name": "Groq",
                "provider_type": ProviderType.llm,
                "description": "Ultra-fast LPU inference for instant storyboard generation.",
                "supports_local": False,
                "capabilities": ["text_generation", "speech_to_text"],
            },
            {
                "name": "local_llm",
                "display_name": "Local LLM (Ollama)",
                "provider_type": ProviderType.llm,
                "description": "100% offline local LLM running on host hardware.",
                "supports_local": True,
                "capabilities": ["text_generation"],
            },
            {
                "name": "local_comfyui",
                "display_name": "Local ComfyUI",
                "provider_type": ProviderType.video,
                "description": "Local node-based diffusion video & image inference engine.",
                "supports_local": True,
                "capabilities": ["video_generation", "image_generation", "image_to_video"],
            },
            {
                "name": "fal_video",
                "display_name": "Fal.ai Video",
                "provider_type": ProviderType.video,
                "description": "High-fidelity cloud video models (Kling, Wan 2.1, LTX-Video).",
                "supports_local": False,
                "capabilities": ["video_generation", "image_to_video"],
            },
            {
                "name": "replicate_video",
                "display_name": "Replicate Video",
                "provider_type": ProviderType.video,
                "description": "Cloud inference for open-source video models.",
                "supports_local": False,
                "capabilities": ["video_generation", "image_to_video"],
            },
            {
                "name": "huggingface_video",
                "display_name": "Hugging Face Video",
                "provider_type": ProviderType.video,
                "description": "Hugging Face Serverless Video Inference API.",
                "supports_local": False,
                "capabilities": ["video_generation", "image_to_video"],
            },
            {
                "name": "local_image",
                "display_name": "Local Image Engine",
                "provider_type": ProviderType.image,
                "description": "Local image generator and composition previewer.",
                "supports_local": True,
                "capabilities": ["image_generation"],
            },
            {
                "name": "huggingface_image",
                "display_name": "Hugging Face Image",
                "provider_type": ProviderType.image,
                "description": "Cloud FLUX and SDXL image generation.",
                "supports_local": False,
                "capabilities": ["image_generation"],
            },
            {
                "name": "local_tts",
                "display_name": "Local Text-to-Speech",
                "provider_type": ProviderType.tts,
                "description": "Native system speech synthesis with zero cloud reliance.",
                "supports_local": True,
                "capabilities": ["text_to_speech"],
            },
            {
                "name": "elevenlabs",
                "display_name": "ElevenLabs",
                "provider_type": ProviderType.tts,
                "description": "Ultra-realistic human voiceover synthesis in 29+ languages.",
                "supports_local": False,
                "capabilities": ["text_to_speech"],
            },
            {
                "name": "local_whisper",
                "display_name": "Local Whisper STT",
                "provider_type": ProviderType.stt,
                "description": "Offline speech-to-text for subtitle alignment.",
                "supports_local": True,
                "capabilities": ["speech_to_text"],
            },
            {
                "name": "groq_whisper",
                "display_name": "Groq Whisper STT",
                "provider_type": ProviderType.stt,
                "description": "Whisper Large V3 transcription running at 200x realtime.",
                "supports_local": False,
                "capabilities": ["speech_to_text"],
            },
        ]

        for p_data in default_providers:
            p_res = await db.execute(select(Provider).where(Provider.name == p_data["name"]))
            existing_p = p_res.scalar_one_or_none()
            if not existing_p:
                prov = Provider(**p_data)
                db.add(prov)
                await db.commit()
                await db.refresh(prov)

                # If it's a local provider, automatically register a default active local account
                if p_data["supports_local"]:
                    local_acc = ProviderAccount(
                        provider_id=prov.id,
                        user_id=admin.id,
                        account_name=f"Default {p_data['display_name']}",
                        encrypted_api_key="LOCAL_UNENCRYPTED_PLACEHOLDER",
                        key_hint="LOCAL-HOST",
                        is_active=True,
                        is_healthy=True,
                        priority=1,
                    )
                    db.add(local_acc)
                    await db.commit()

        logger.info("initial_providers_seeded_successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown lifecycle events."""
    logger.info("app_starting_up", app=settings.APP_NAME, env=settings.APP_ENV)

    # 1. Ensure storage directories exist
    for p in [settings.STORAGE_BASE_PATH, settings.PROJECTS_PATH, settings.ASSETS_PATH, settings.RENDERS_PATH, settings.TEMP_PATH]:
        Path(p).mkdir(parents=True, exist_ok=True)

    # 2. Initialize database & seed initial defaults
    try:
        await init_db()
        await seed_initial_data()
    except Exception as e:
        logger.warning("database_init_warning", error=str(e))

    # 3. Hardware inspection
    hw = detect_hardware()
    logger.info(
        "hardware_detected",
        os=hw.os_name,
        arch=hw.arch,
        ram_gb=hw.ram_gb,
        apple_silicon=hw.is_apple_silicon,
        ffmpeg=hw.ffmpeg_available,
        comfyui=hw.comfyui_running,
    )

    yield

    logger.info("app_shutting_down")


app = FastAPI(
    title="Local AI Video Production Studio",
    description="Production-grade local-first video generation studio with intelligent API rotation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware (Next.js frontend support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts for downloads and browser video playback
renders_path = os.path.abspath(settings.RENDERS_PATH)
assets_path = os.path.abspath(settings.ASSETS_PATH)
os.makedirs(renders_path, exist_ok=True)
os.makedirs(assets_path, exist_ok=True)

app.mount("/renders", StaticFiles(directory=renders_path), name="renders")
app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

# Include master REST API v1
app.include_router(api_router)


# Realtime WebSocket endpoint for job status
@app.websocket("/ws/{job_id}")
async def websocket_job_endpoint(websocket: WebSocket, job_id: str):
    """Realtime WebSocket channel for job progress, scene rendering updates, and logs."""
    await ws_manager.connect(websocket, job_id)
    try:
        while True:
            # Keepalive listener
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)
    except Exception:
        ws_manager.disconnect(websocket, job_id)


@app.get("/health")
async def root_health():
    """Root health check endpoint."""
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "version": "1.0.0",
    }
