"""
ComfyUI local video/image generation provider.

Communicates with a running ComfyUI instance via its REST API.
Workflows are loaded from workflows/comfyui/{name}.json relative to
the project root.

Supports:
  - TEXT_TO_VIDEO  (txt2vid workflows)
  - IMAGE_TO_VIDEO (img2vid workflows)
"""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
import structlog

from backend.providers.base.provider_interface import (
    BaseProvider,
    ErrorType,
    GenerationRequest,
    GenerationResult,
    ProviderCapability,
    ProviderHealth,
)

logger = structlog.get_logger(__name__)

_DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"
_POLL_INTERVAL = 3.0      # seconds between status polls
_DEFAULT_TIMEOUT = 300    # seconds to wait for completion

# Paths relative to project root
_WORKFLOW_DIR = Path(__file__).resolve().parents[4] / "workflows" / "comfyui"

# ComfyUI node class types that hold prompt text
_POSITIVE_CLASSES = {"CLIPTextEncode"}
_NEGATIVE_TITLES = {"negative", "neg prompt", "negative prompt"}
_POSITIVE_TITLES = {"positive", "pos prompt", "positive prompt"}


class ComfyUIProvider(BaseProvider):
    """Local ComfyUI provider for video and image generation."""

    name = "local_comfyui"
    display_name = "Local ComfyUI"
    capabilities = [
        ProviderCapability.VIDEO_GENERATION,
        ProviderCapability.IMAGE_TO_VIDEO,
        ProviderCapability.IMAGE_GENERATION,
    ]
    is_local = True

    def __init__(self, base_url: str = _DEFAULT_COMFYUI_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self._client_id = str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Connectivity helpers
    # ------------------------------------------------------------------

    async def detect_running(self) -> bool:
        """Return True if ComfyUI is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/system_stats")
                return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Workflow management
    # ------------------------------------------------------------------

    def load_workflow(self, workflow_name: str) -> dict:
        """Load a ComfyUI workflow JSON from disk.

        workflow_name should be the bare name (without .json extension).
        """
        path = _WORKFLOW_DIR / f"{workflow_name}.json"
        if not path.exists():
            # Also check relative to CWD
            alt_path = Path("workflows") / "comfyui" / f"{workflow_name}.json"
            if alt_path.exists():
                path = alt_path
            else:
                raise FileNotFoundError(
                    f"Workflow not found: {path}. "
                    "Create it in workflows/comfyui/{workflow_name}.json"
                )

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def inject_prompts(
        self,
        workflow: dict,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
    ) -> dict:
        """Inject positive / negative prompts into workflow nodes.

        Strategy:
        1. Find CLIPTextEncode nodes
        2. Distinguish positive vs negative by node title or metadata
        3. Inject text into the 'text' input field
        """
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue

            class_type = node.get("class_type", "")
            title = node.get("_meta", {}).get("title", "").lower()

            if class_type not in _POSITIVE_CLASSES:
                continue

            # Classify as positive or negative by title keywords
            if any(neg in title for neg in _NEGATIVE_TITLES):
                if negative_prompt is not None:
                    node["inputs"]["text"] = negative_prompt
            elif any(pos in title for pos in _POSITIVE_TITLES) or not any(
                neg in title for neg in _NEGATIVE_TITLES
            ):
                # Default: treat un-titled CLIPTextEncode as positive
                node["inputs"]["text"] = positive_prompt

        return workflow

    def inject_seed(self, workflow: dict, seed: Optional[int]) -> dict:
        """Set a specific seed in KSampler / SamplerCustom nodes."""
        if seed is None:
            return workflow
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") in {"KSampler", "KSamplerAdvanced", "SamplerCustom"}:
                if "seed" in node.get("inputs", {}):
                    node["inputs"]["seed"] = seed
        return workflow

    # ------------------------------------------------------------------
    # ComfyUI API calls
    # ------------------------------------------------------------------

    async def submit_workflow(self, workflow: dict) -> str:
        """POST workflow to /prompt. Returns prompt_id."""
        payload = {
            "prompt": workflow,
            "client_id": self._client_id,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/prompt", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["prompt_id"]

    async def check_job_status(self, prompt_id: str) -> dict:
        """GET /history/{prompt_id}. Returns status dict."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            data = response.json()
            return data.get(prompt_id, {})

    async def wait_for_completion(
        self, prompt_id: str, timeout: int = _DEFAULT_TIMEOUT
    ) -> dict:
        """Poll /history until the job appears and finishes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                status = await self.check_job_status(prompt_id)
                if status:
                    return status
            except Exception as exc:
                logger.warning("comfyui_poll_error", error=str(exc), prompt_id=prompt_id)
            await asyncio.sleep(_POLL_INTERVAL)

        raise TimeoutError(
            f"ComfyUI job {prompt_id} did not complete within {timeout}s"
        )

    async def retrieve_output(
        self, job_status: dict, output_dir: str
    ) -> Optional[str]:
        """Download the generated output file and return local path."""
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        outputs = job_status.get("outputs", {})
        for node_id, node_output in outputs.items():
            # Video outputs
            for video in node_output.get("videos", []):
                filename = video.get("filename")
                subfolder = video.get("subfolder", "")
                if filename:
                    url = f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type=output"
                    local_path = output_dir_path / filename
                    await self._download_file(url, local_path)
                    return str(local_path)

            # Image outputs
            for image in node_output.get("images", []):
                filename = image.get("filename")
                subfolder = image.get("subfolder", "")
                if filename:
                    url = f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type=output"
                    local_path = output_dir_path / filename
                    await self._download_file(url, local_path)
                    return str(local_path)

        return None

    async def _download_file(self, url: str, local_path: Path) -> None:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

    async def cancel_job(self, prompt_id: str) -> None:
        """Interrupt the currently running ComfyUI job."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{self.base_url}/interrupt")
                logger.info("comfyui_job_cancelled", prompt_id=prompt_id)
        except Exception as exc:
            logger.warning("comfyui_cancel_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate video using a ComfyUI workflow."""
        start_ms = int(time.monotonic() * 1000)

        if not await self.detect_running():
            return GenerationResult(
                success=False,
                error_type=ErrorType.SERVER_ERROR,
                error_message=(
                    f"ComfyUI is not running at {self.base_url}. "
                    "Start ComfyUI and try again."
                ),
            )

        # Select workflow
        if request.reference_images:
            workflow_name = request.extra_params.get("workflow", "img2vid_default")
        else:
            workflow_name = request.extra_params.get("workflow", "txt2vid_default")

        try:
            workflow = self.load_workflow(workflow_name)
        except FileNotFoundError as exc:
            return GenerationResult(
                success=False,
                error_type=ErrorType.INVALID_REQUEST,
                error_message=str(exc),
            )

        # Inject prompts and seed
        workflow = self.inject_prompts(workflow, request.prompt, request.negative_prompt)
        workflow = self.inject_seed(workflow, request.seed)

        # Inject reference image path if provided
        if request.reference_images:
            for node_id, node in workflow.items():
                if isinstance(node, dict) and node.get("class_type") == "LoadImage":
                    node["inputs"]["image"] = request.reference_images[0]
                    break

        try:
            prompt_id = await self.submit_workflow(workflow)
            logger.info("comfyui_job_submitted", prompt_id=prompt_id, workflow=workflow_name)

            job_status = await self.wait_for_completion(
                prompt_id,
                timeout=request.extra_params.get("timeout", _DEFAULT_TIMEOUT),
            )

            from backend.core.config import get_settings
            settings = get_settings()
            output_dir = getattr(settings, "OUTPUT_DIR", "outputs/videos")

            output_path = await self.retrieve_output(job_status, output_dir)
            elapsed = int(time.monotonic() * 1000) - start_ms

            if output_path:
                logger.info(
                    "comfyui_generation_success",
                    prompt_id=prompt_id,
                    output=output_path,
                    duration_ms=elapsed,
                )
                return GenerationResult(
                    success=True,
                    output_path=output_path,
                    provider_job_id=prompt_id,
                    model_used=workflow_name,
                    duration_ms=elapsed,
                    metadata={"workflow": workflow_name, "prompt_id": prompt_id},
                )
            else:
                return GenerationResult(
                    success=False,
                    error_type=ErrorType.SERVER_ERROR,
                    error_message="ComfyUI job completed but no output file was found.",
                    provider_job_id=prompt_id,
                    duration_ms=elapsed,
                )

        except TimeoutError as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            return GenerationResult(
                success=False,
                error_type=ErrorType.TIMEOUT,
                error_message=str(exc),
                duration_ms=elapsed,
            )

        except Exception as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            error_type = self.classify_error(exc)
            logger.error(
                "comfyui_generation_error",
                error_class=type(exc).__name__,
                error=str(exc),
                duration_ms=elapsed,
            )
            return GenerationResult(
                success=False,
                error_type=error_type,
                error_message=str(exc),
                duration_ms=elapsed,
            )

    async def generate_image(self, request: GenerationRequest) -> GenerationResult:
        """Route image generation through ComfyUI."""
        # Reuse the same logic but with an image workflow
        img_request = GenerationRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            seed=request.seed,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            extra_params={**request.extra_params, "workflow": request.extra_params.get("workflow", "txt2img_default")},
        )
        result = await self.generate_video(img_request)  # Same code path
        return result

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        start_ms = int(time.monotonic() * 1000)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                response.raise_for_status()
                data = response.json()

            latency = int(time.monotonic() * 1000) - start_ms
            return ProviderHealth(
                is_available=True,
                latency_ms=latency,
                quota_status="healthy",
                error_message=None,
            )

        except httpx.ConnectError:
            latency = int(time.monotonic() * 1000) - start_ms
            return ProviderHealth(
                is_available=False,
                latency_ms=latency,
                quota_status="unknown",
                error_message=f"ComfyUI not reachable at {self.base_url}",
            )

        except Exception as exc:
            latency = int(time.monotonic() * 1000) - start_ms
            return ProviderHealth(
                is_available=False,
                latency_ms=latency,
                quota_status="unknown",
                error_message=str(exc),
            )
