"""Scene Manager and State Persistence.

Manages individual scene asset folders, scene state persistence (state.json),
resume logic for interrupted jobs, and reference image propagation.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import List, Optional

import structlog

from backend.models.scene import Scene, SceneStatus

logger = structlog.get_logger(__name__)


class SceneManager:
    """Manages scene directories, per-scene artifacts, and resume checkpointing."""

    def __init__(self, projects_root: str):
        self.projects_root = Path(projects_root)
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def get_scene_dir(self, project_id: str, scene_number: int) -> Path:
        scene_dir = self.projects_root / str(project_id) / "scenes" / f"scene_{scene_number:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        return scene_dir

    def save_scene_state(self, project_id: str, scene: Scene, extra: Optional[dict] = None):
        """Save scene checkpoint state.json for zero-data-loss resumption."""
        scene_dir = self.get_scene_dir(project_id, scene.scene_number)
        state_file = scene_dir / "state.json"

        state_data = {
            "scene_id": str(scene.id),
            "project_id": str(project_id),
            "scene_number": scene.scene_number,
            "status": scene.status.value if hasattr(scene.status, "value") else str(scene.status),
            "title": scene.title,
            "duration_seconds": scene.duration_seconds,
            "image_prompt": scene.image_prompt,
            "video_prompt": scene.video_prompt,
            "voice_over": scene.voice_over,
            "video_path": scene.video_path,
            "image_path": scene.image_path,
            "audio_path": scene.audio_path,
            "provider_used": scene.provider_used,
            "retry_count": scene.retry_count,
            "error_message": scene.error_message,
        }
        if extra:
            state_data.update(extra)

        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.warning("save_scene_state_failed", error=str(e), path=str(state_file))

    def load_scene_state(self, project_id: str, scene_number: int) -> Optional[dict]:
        state_file = self.get_scene_dir(project_id, scene_number) / "state.json"
        if not state_file.exists():
            return None
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def is_scene_valid(self, project_id: str, scene_number: int) -> bool:
        """Check whether a scene clip already exists and is non-empty for resumption."""
        scene_dir = self.get_scene_dir(project_id, scene_number)
        vid_file = scene_dir / "video.mp4"
        return vid_file.exists() and vid_file.stat().st_size > 1024

    def copy_reference_asset(self, asset_path: str, project_id: str, scene_number: int) -> str:
        """Copy a reference image into the scene folder for inference consistency."""
        scene_dir = self.get_scene_dir(project_id, scene_number)
        dest = scene_dir / f"reference_{Path(asset_path).name}"
        if Path(asset_path).exists():
            shutil.copy2(asset_path, dest)
            return str(dest)
        return asset_path
