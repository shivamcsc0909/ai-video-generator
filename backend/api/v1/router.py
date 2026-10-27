"""API v1 master router."""

from fastapi import APIRouter

from backend.api.v1 import (
    assets,
    auth,
    generations,
    projects,
    providers,
    scenes,
    system,
    voice,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(generations.router, prefix="/generations", tags=["generations"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
