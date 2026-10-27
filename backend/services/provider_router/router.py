"""Provider Router with multi-account rotation, error classification, and failover."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Callable, List, Optional
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.provider import Provider, ProviderAccount, ProviderUsage, ProviderFailure
from backend.models.system_settings import ApiUsageLog
from backend.providers.base.provider_interface import (
    BaseProvider,
    ErrorType,
    GenerationRequest,
    GenerationResult,
    ProviderCapability,
)
from backend.services.credentials.encryption import get_encryption_service
from backend.services.provider_router.scorer import ProviderScorer

logger = structlog.get_logger(__name__)


class ProviderRouter:
    """Smart Provider Router.

    Dynamically selects the optimal provider account based on capability,
    scores, user quality mode, and hardware availability.
    Implements multi-account rotation (e.g. Gemini Account 1 -> 2 -> 3),
    retry policies, rate-limit cooldowns, and automatic failover.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scorer = ProviderScorer()
        self.encryption = get_encryption_service()

    # -------------------------------------------------------------------------
    # Public Routing Facades
    # -------------------------------------------------------------------------

    async def route_text_generation(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        quality_mode: str = "balanced",
        job_id: Optional[str] = None,
    ) -> GenerationResult:
        """Route LLM generation to best available account/provider."""
        return await self._execute_with_failover(
            capability=ProviderCapability.TEXT_GENERATION,
            operation_name="text_generation",
            execute_fn=lambda p: p.generate_text(prompt=prompt, system_prompt=system_prompt),
            quality_mode=quality_mode,
            job_id=job_id,
        )

    async def route_video_generation(
        self,
        request: GenerationRequest,
        quality_mode: str = "balanced",
        job_id: Optional[str] = None,
    ) -> GenerationResult:
        """Route video generation to best local or remote provider."""
        cap = (
            ProviderCapability.IMAGE_TO_VIDEO
            if request.reference_images and len(request.reference_images) > 0
            else ProviderCapability.VIDEO_GENERATION
        )
        return await self._execute_with_failover(
            capability=cap,
            operation_name="video_generation",
            execute_fn=lambda p: p.generate_video(request),
            quality_mode=quality_mode,
            job_id=job_id,
        )

    async def route_image_generation(
        self,
        request: GenerationRequest,
        quality_mode: str = "balanced",
        job_id: Optional[str] = None,
    ) -> GenerationResult:
        """Route image generation to local engine or cloud image models."""
        return await self._execute_with_failover(
            capability=ProviderCapability.IMAGE_GENERATION,
            operation_name="image_generation",
            execute_fn=lambda p: p.generate_image(request),
            quality_mode=quality_mode,
            job_id=job_id,
        )

    async def route_tts(
        self,
        text: str,
        voice_settings: dict,
        output_path: str,
        quality_mode: str = "balanced",
        job_id: Optional[str] = None,
    ) -> GenerationResult:
        """Route TTS generation to local speech engine or ElevenLabs."""
        return await self._execute_with_failover(
            capability=ProviderCapability.TEXT_TO_SPEECH,
            operation_name="text_to_speech",
            execute_fn=lambda p: p.generate_audio(
                text=text,
                voice_settings=voice_settings,
                output_path=output_path,
            ),
            quality_mode=quality_mode,
            job_id=job_id,
        )

    async def route_stt(
        self,
        audio_path: str,
        language: Optional[str] = None,
        quality_mode: str = "balanced",
        job_id: Optional[str] = None,
    ) -> GenerationResult:
        """Route STT to local Whisper or Groq Whisper."""
        return await self._execute_with_failover(
            capability=ProviderCapability.SPEECH_TO_TEXT,
            operation_name="speech_to_text",
            execute_fn=lambda p: p.transcribe(audio_path=audio_path, language=language),
            quality_mode=quality_mode,
            job_id=job_id,
        )

    # -------------------------------------------------------------------------
    # Core Failover & Multi-Account Execution Engine
    # -------------------------------------------------------------------------

    async def _execute_with_failover(
        self,
        capability: ProviderCapability,
        operation_name: str,
        execute_fn: Callable[[BaseProvider], any],
        quality_mode: str,
        job_id: Optional[str] = None,
    ) -> GenerationResult:
        eligible_candidates = await self._get_eligible_candidates(capability, quality_mode)

        if not eligible_candidates:
            # Check if there are default local fallback options
            fallback_instance = self._get_default_local_provider(capability)
            if fallback_instance:
                try:
                    logger.info("using_default_local_fallback", capability=capability.value)
                    return await execute_fn(fallback_instance)
                except Exception as e:
                    logger.error("default_local_fallback_failed", error=str(e))

            return GenerationResult(
                success=False,
                error_type=ErrorType.MODEL_UNAVAILABLE,
                error_message=(
                    f"No active provider configured for capability: {capability.value}. "
                    "Please configure an AI provider account under Settings → AI Providers."
                ),
            )

        attempted_accounts = set()
        last_error_result: Optional[GenerationResult] = None

        for cand in eligible_candidates:
            account = cand["account"]
            provider = cand["provider"]
            provider_instance = cand["instance"]
            acc_id = str(account.id)

            if acc_id in attempted_accounts:
                continue
            attempted_accounts.add(acc_id)

            logger.info(
                "provider_candidate_attempt",
                provider=provider.name,
                account=account.account_name,
                key_hint=account.key_hint,
                capability=capability.value,
                job_id=job_id,
            )

            # Retry loop for transient issues (max 2 retries)
            for attempt in range(2):
                start_time = datetime.utcnow()
                try:
                    res: GenerationResult = await execute_fn(provider_instance)
                    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                    if res.success:
                        await self._record_success(account, provider, operation_name, duration_ms, res, job_id)
                        return res

                    # Provider returned a structured error
                    error_type = res.error_type or ErrorType.UNKNOWN
                    await self._record_failure(account, provider, error_type, res.error_message or "Unknown error", job_id)
                    last_error_result = res

                except Exception as ex:
                    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    error_type = provider_instance.classify_error(ex)
                    err_msg = str(ex)
                    last_error_result = GenerationResult(
                        success=False,
                        error_type=error_type,
                        error_message=err_msg,
                    )
                    await self._record_failure(account, provider, error_type, err_msg, job_id)

                # Evaluate error classification for rotation & cooldown
                if error_type == ErrorType.AUTH_ERROR:
                    logger.warning("provider_auth_error_disabling", account=account.account_name)
                    account.is_active = False
                    account.is_healthy = False
                    account.last_error_message = f"Authentication error: {last_error_result.error_message[:200]}"
                    await self.db.commit()
                    break  # Rotate to next account immediately

                elif error_type in (ErrorType.RATE_LIMIT, ErrorType.QUOTA_EXCEEDED):
                    cooldown_minutes = 15 if error_type == ErrorType.RATE_LIMIT else 60
                    logger.info(
                        "provider_rate_limit_cooldown",
                        account=account.account_name,
                        minutes=cooldown_minutes,
                    )
                    account.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
                    await self.db.commit()
                    break  # Rotate to next account immediately

                elif error_type == ErrorType.INVALID_REQUEST:
                    # Invalid parameters or prompt syntax won't succeed on next account either
                    return last_error_result

                elif error_type in (ErrorType.TRANSIENT, ErrorType.SERVER_ERROR, ErrorType.TIMEOUT):
                    if attempt == 0:
                        await asyncio.sleep(1.5)
                        continue  # Retry same account once
                    break  # Rotate to next account

                else:
                    break

        # If all configured accounts failed, attempt local fallback if applicable
        if not any(c["provider"].supports_local for c in eligible_candidates):
            local_fallback = self._get_default_local_provider(capability)
            if local_fallback:
                try:
                    logger.info("all_remote_accounts_failed_attempting_local_fallback", capability=capability.value)
                    local_res = await execute_fn(local_fallback)
                    if local_res.success:
                        return local_res
                except Exception as fallback_err:
                    logger.warning("local_fallback_also_failed", error=str(fallback_err))

        return last_error_result or GenerationResult(
            success=False,
            error_type=ErrorType.MODEL_UNAVAILABLE,
            error_message="All configured providers failed to execute this request.",
        )

    # -------------------------------------------------------------------------
    # Candidate Discovery & Scoring
    # -------------------------------------------------------------------------

    async def _get_eligible_candidates(
        self, capability: ProviderCapability, quality_mode: str
    ) -> List[dict]:
        stmt = (
            select(ProviderAccount, Provider)
            .join(Provider, ProviderAccount.provider_id == Provider.id)
            .where(ProviderAccount.is_active == True)
            .where(Provider.is_enabled == True)
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        scored = []
        for account, provider in rows:
            # Check capability support
            caps = provider.capabilities or []
            if capability.value not in caps:
                continue

            score = self.scorer.score_account(account, provider, quality_mode)
            if not score.is_eligible:
                continue

            instance = self._instantiate_provider(account, provider)
            if not instance:
                continue

            scored.append({
                "account": account,
                "provider": provider,
                "instance": instance,
                "score": score.total_score,
            })

        # Sort descending by total score
        scored.sort(key=lambda x: x["score"], reverse=True)

        # In 'local' mode, prioritize local providers first
        if quality_mode == "local":
            scored.sort(key=lambda x: 1 if x["provider"].supports_local else 0, reverse=True)

        return scored

    def _instantiate_provider(
        self, account: ProviderAccount, provider: Provider
    ) -> Optional[BaseProvider]:
        name = provider.name
        try:
            # Decrypt API key for remote providers
            api_key = ""
            if not provider.supports_local and account.encrypted_api_key:
                api_key = self.encryption.decrypt(account.encrypted_api_key)

            if name == "google_gemini":
                from backend.providers.llm.gemini import GeminiProvider
                return GeminiProvider(api_key=api_key)
            elif name == "groq":
                from backend.providers.llm.groq_provider import GroqProvider
                return GroqProvider(api_key=api_key)
            elif name == "local_llm":
                from backend.providers.llm.local_llm import LocalLLMProvider
                return LocalLLMProvider()
            elif name == "local_comfyui":
                from backend.providers.video.local_comfyui import ComfyUIProvider
                return ComfyUIProvider()
            elif name == "fal_video":
                from backend.providers.video.fal import FalVideoProvider
                return FalVideoProvider(api_key=api_key)
            elif name == "replicate_video":
                from backend.providers.video.replicate import ReplicateVideoProvider
                return ReplicateVideoProvider(api_key=api_key)
            elif name == "huggingface_video":
                from backend.providers.video.huggingface import HuggingFaceVideoProvider
                return HuggingFaceVideoProvider(api_key=api_key)
            elif name == "local_image":
                from backend.providers.image.local_image import LocalImageProvider
                return LocalImageProvider()
            elif name == "huggingface_image":
                from backend.providers.image.huggingface import HuggingFaceImageProvider
                return HuggingFaceImageProvider(api_key=api_key)
            elif name == "local_tts":
                from backend.providers.tts.local_tts import LocalTTSProvider
                return LocalTTSProvider()
            elif name == "elevenlabs":
                from backend.providers.tts.elevenlabs import ElevenLabsProvider
                return ElevenLabsProvider(api_key=api_key)
            elif name == "local_whisper":
                from backend.providers.stt.local_whisper import LocalWhisperProvider
                return LocalWhisperProvider()
            elif name == "groq_whisper":
                from backend.providers.stt.groq_whisper import GroqWhisperProvider
                return GroqWhisperProvider(api_key=api_key)
        except Exception as e:
            logger.error("failed_to_instantiate_provider", provider=provider.name, error=str(e))
        return None

    def _get_default_local_provider(self, capability: ProviderCapability) -> Optional[BaseProvider]:
        """Provides default zero-credential local provider when no user accounts are configured."""
        if capability in (ProviderCapability.VIDEO_GENERATION, ProviderCapability.IMAGE_TO_VIDEO):
            from backend.providers.video.local_comfyui import ComfyUIProvider
            return ComfyUIProvider()
        elif capability == ProviderCapability.IMAGE_GENERATION:
            from backend.providers.image.local_image import LocalImageProvider
            return LocalImageProvider()
        elif capability == ProviderCapability.TEXT_TO_SPEECH:
            from backend.providers.tts.local_tts import LocalTTSProvider
            return LocalTTSProvider()
        elif capability == ProviderCapability.SPEECH_TO_TEXT:
            from backend.providers.stt.local_whisper import LocalWhisperProvider
            return LocalWhisperProvider()
        elif capability == ProviderCapability.TEXT_GENERATION:
            from backend.providers.llm.local_llm import LocalLLMProvider
            return LocalLLMProvider()
        return None

    # -------------------------------------------------------------------------
    # Metrics & Logging
    # -------------------------------------------------------------------------

    async def _record_success(
        self,
        account: ProviderAccount,
        provider: Provider,
        operation: str,
        duration_ms: int,
        result: GenerationResult,
        job_id: Optional[str],
    ):
        try:
            account.success_count += 1
            account.last_success_at = datetime.utcnow()
            account.is_healthy = True
            account.daily_request_count += 1

            # Update rolling latency
            if account.avg_latency_ms:
                account.avg_latency_ms = (account.avg_latency_ms * 0.8) + (duration_ms * 0.2)
            else:
                account.avg_latency_ms = float(duration_ms)

            # Audit log
            log_entry = ApiUsageLog(
                account_id=account.id,
                provider_name=provider.name,
                model_name=result.model_used,
                job_id=job_id,
                operation=operation,
                duration_ms=duration_ms,
                success=True,
                estimated_cost=result.estimated_cost,
            )
            self.db.add(log_entry)
            await self.db.commit()
        except Exception as e:
            logger.warning("metrics_recording_failed", error=str(e))

    async def _record_failure(
        self,
        account: ProviderAccount,
        provider: Provider,
        error_type: ErrorType,
        error_message: str,
        job_id: Optional[str],
    ):
        try:
            account.failure_count += 1
            account.last_error_at = datetime.utcnow()
            account.last_error_message = error_message[:500]

            failure = ProviderFailure(
                account_id=account.id,
                error_type=error_type.value,
                error_message=error_message[:1000],
                job_id=job_id,
            )
            self.db.add(failure)

            log_entry = ApiUsageLog(
                account_id=account.id,
                provider_name=provider.name,
                job_id=job_id,
                operation="error",
                duration_ms=0,
                success=False,
                error_type=error_type.value,
            )
            self.db.add(log_entry)
            await self.db.commit()
        except Exception as e:
            logger.warning("failure_recording_failed", error=str(e))
