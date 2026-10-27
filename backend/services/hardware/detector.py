"""System hardware detection service.

Detects Apple Silicon, RAM/unified memory, MPS/CUDA, disk space, FFmpeg, and ComfyUI.
Recommends optimal local vs API configuration for 16GB Apple Silicon or current host.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Optional

import psutil
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HardwareInfo:
    os_name: str
    os_version: str
    arch: str
    cpu_model: str
    cpu_cores: int
    ram_gb: float
    is_apple_silicon: bool
    gpu_name: Optional[str]
    has_cuda: bool
    has_mps: bool
    available_disk_gb: float
    python_version: str
    ffmpeg_available: bool
    ffmpeg_version: Optional[str]
    comfyui_running: bool
    recommended_config: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_hardware() -> HardwareInfo:
    os_name = platform.system()
    os_version = platform.version()
    arch = platform.machine()
    cpu_model = platform.processor() or arch
    cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)

    # Apple Silicon detection (macOS + arm64)
    is_apple_silicon = (os_name == "Darwin" and arch == "arm64")

    # Torch / GPU acceleration check
    gpu_name = None
    has_cuda = False
    has_mps = False

    try:
        import torch

        has_cuda = torch.cuda.is_available()
        has_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        if has_cuda:
            gpu_name = torch.cuda.get_device_name(0)
        elif has_mps:
            gpu_name = "Apple Silicon GPU (MPS Metal Acceleration)"
    except Exception:
        pass

    if not gpu_name and is_apple_silicon:
        gpu_name = "Apple Silicon Unified Memory GPU"

    # Disk space available in storage directory
    try:
        disk = psutil.disk_usage(os.getcwd())
        available_disk_gb = round(disk.free / (1024**3), 1)
    except Exception:
        available_disk_gb = 50.0

    # Python version
    python_version = platform.python_version()

    # FFmpeg binary check (check PATH, common Homebrew paths)
    ffmpeg_paths = [
        shutil.which("ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ]
    ffmpeg_bin = next((p for p in ffmpeg_paths if p and os.path.exists(p)), None)
    ffmpeg_available = ffmpeg_bin is not None
    ffmpeg_version = None

    if ffmpeg_available and ffmpeg_bin:
        try:
            res = subprocess.run(
                [ffmpeg_bin, "-version"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and "version" in res.stdout:
                ffmpeg_version = res.stdout.split("\n")[0].split("version ")[1].split(" ")[0]
        except Exception:
            ffmpeg_version = "installed"

    # Check if local ComfyUI is running
    comfyui_running = False
    try:
        import urllib.request
        from backend.core.config import get_settings

        settings = get_settings()
        url = f"{settings.COMFYUI_URL}/system_stats"
        req = urllib.request.Request(url, headers={"User-Agent": "AIVideoStudio/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            comfyui_running = (resp.status == 200)
    except Exception:
        comfyui_running = False

    # Recommend appropriate configuration
    if is_apple_silicon and ram_gb <= 18:
        recommended_config = (
            f"Apple Silicon ({ram_gb} GB unified): Balanced Mode recommended. "
            "Use quantized local models or ComfyUI AnimateDiff at 512p for local clips, "
            "and external AI providers (Gemini, Groq, Fal/Replicate) for long scenes and complex rendering."
        )
    elif ram_gb <= 8:
        recommended_config = (
            f"Low memory ({ram_gb} GB): Free/Balanced with API providers recommended. "
            "Local deep learning video inference may exceed available RAM."
        )
    elif has_cuda:
        recommended_config = (
            f"NVIDIA GPU ({gpu_name}): Full local generation supported. "
            "Local ComfyUI, SDXL, and Stable Video Diffusion are optimal."
        )
    else:
        recommended_config = (
            f"Host ({ram_gb} GB RAM, CPU): Balanced Mode with local audio/FFmpeg and "
            "configured AI providers for video generation."
        )

    return HardwareInfo(
        os_name=os_name,
        os_version=os_version,
        arch=arch,
        cpu_model=cpu_model,
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        is_apple_silicon=is_apple_silicon,
        gpu_name=gpu_name,
        has_cuda=has_cuda,
        has_mps=has_mps,
        available_disk_gb=available_disk_gb,
        python_version=python_version,
        ffmpeg_available=ffmpeg_available,
        ffmpeg_version=ffmpeg_version,
        comfyui_running=comfyui_running,
        recommended_config=recommended_config,
    )
