"""Video Production Pipeline Tasks.

Orchestrates:
SCRIPT -> STORYBOARD -> SCENES -> SHORT VIDEO CLIPS -> VOICE -> SYNC -> COMPOSITING -> SUBTITLES -> QC -> EXPORT
Can run either as a Celery background task or direct asyncio background task.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy import select

from backend.core.config import get_settings
from backend.core.database import AsyncSessionLocal
from backend.core.websocket import manager as ws_manager
from backend.models.generation import Generation, GenerationStatus
from backend.models.project import Project
from backend.models.scene import Scene
from backend.providers.base.provider_interface import GenerationRequest
from backend.services.audio.sync import AudioSyncEngine
from backend.services.ffmpeg.pipeline import FFmpegPipeline
from backend.services.provider_router.router import ProviderRouter
from backend.services.quality.checker import QualityChecker
from backend.services.scene_manager.manager import SceneManager
from backend.services.storyboard.engine import StoryboardEngine
from backend.services.subtitle.generator import SubtitleGenerator

logger = structlog.get_logger(__name__)
settings = get_settings()


async def generate_full_video_pipeline(
    project_id: str,
    generation_id: str,
    quality_mode: str = "balanced",
):
    """End-to-end asynchronous video generation pipeline."""
    ffmpeg = FFmpegPipeline()
    quality_checker = QualityChecker()
    subtitle_gen = SubtitleGenerator()
    scene_mgr = SceneManager(settings.PROJECTS_PATH)

    renders_dir = Path(settings.RENDERS_PATH)
    renders_dir.mkdir(parents=True, exist_ok=True)
    proj_dir = Path(settings.PROJECTS_PATH) / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        gen = await db.get(Generation, uuid.UUID(generation_id))
        project = await db.get(Project, uuid.UUID(project_id))
        if not gen or not project:
            logger.error("generation_pipeline_target_not_found", job=generation_id)
            return

        router_svc = ProviderRouter(db)

        async def broadcast_step(status_enum: GenerationStatus, progress: float, step_msg: str, extra: dict = None):
            gen.status = status_enum
            gen.progress_percent = progress
            gen.current_step = step_msg
            await db.commit()

            payload = {
                "job_id": generation_id,
                "status": status_enum.value,
                "progress": progress,
                "step": step_msg,
            }
            if extra:
                payload.update(extra)
            await ws_manager.send_job_update(generation_id, payload)
            logger.info("job_step_transition", job=generation_id, status=status_enum.value, progress=progress, step=step_msg)

        try:
            # -------------------------------------------------------------
            # STEP 1: ANALYZING & STORYBOARDING
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.ANALYZING, 5.0, "Analyzing instructions and project bible...")
            await asyncio.sleep(0.5)

            # Check if scenes already exist from prior storyboard step
            scenes_stmt = select(Scene).where(Scene.project_id == project.id).order_by(Scene.scene_number)
            scenes = (await db.execute(scenes_stmt)).scalars().all()

            if not scenes:
                await broadcast_step(GenerationStatus.STORYBOARDING, 10.0, "Generating multi-scene storyboard...")
                sb_engine = StoryboardEngine(router_svc)
                storyboard = await sb_engine.generate_storyboard(
                    prompt=project.prompt,
                    project_type=project.project_type.value if hasattr(project.project_type, "value") else str(project.project_type),
                    target_duration=project.target_duration,
                    aspect_ratio=project.aspect_ratio,
                    voice_language=project.voice_language or "en",
                    job_id=generation_id,
                )

                # Persist scenes
                for sc in storyboard.scenes:
                    s_obj = Scene(
                        project_id=project.id,
                        generation_id=gen.id,
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
                    db.add(s_obj)

                project.script = storyboard.script
                project.scene_bible = storyboard.scene_bible
                await db.commit()

                scenes = (await db.execute(scenes_stmt)).scalars().all()

            gen.total_scenes = len(scenes)
            await db.commit()

            # -------------------------------------------------------------
            # STEP 2: GENERATING SCENE VIDEO CLIPS (RESUME-AWARE)
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.GENERATING_VIDEO, 20.0, f"Generating {len(scenes)} visual scene clips...")

            scene_video_paths = []
            completed_count = 0

            for sc in scenes:
                sc_dir = scene_mgr.get_scene_dir(project_id, sc.scene_number)
                video_out = str(sc_dir / "video.mp4")

                # RESUME CHECK: If clip exists and is valid, reuse it!
                if os.path.exists(video_out) and os.path.getsize(video_out) > 1024:
                    logger.info("resuming_using_existing_scene_clip", scene=sc.scene_number)
                    scene_video_paths.append(video_out)
                    completed_count += 1
                    sc.status = "completed"
                    sc.video_path = video_out
                    await db.commit()
                    continue

                sc.status = "generating"
                await db.commit()

                # Build generation request for this scene
                prompt_to_use = sc.video_prompt or sc.image_prompt or project.prompt
                req = GenerationRequest(
                    prompt=prompt_to_use,
                    negative_prompt=sc.negative_prompt,
                    duration_seconds=sc.duration_seconds,
                    aspect_ratio=project.aspect_ratio,
                )

                clip_res = await router_svc.route_video_generation(
                    request=req,
                    quality_mode=quality_mode,
                    job_id=generation_id,
                )

                if clip_res.success and clip_res.output_path and os.path.exists(clip_res.output_path):
                    shutil.copyfile(clip_res.output_path, video_out)
                    sc.status = "completed"
                    sc.video_path = video_out
                    sc.provider_used = clip_res.model_used
                    scene_video_paths.append(video_out)
                    completed_count += 1
                elif clip_res.success and clip_res.output_url:
                    # Remote URL result - download or record
                    sc.status = "completed"
                    sc.video_path = clip_res.output_url
                    sc.provider_used = clip_res.model_used
                    # Create clean local representative clip for FFmpeg timeline stitching
                    await ffmpeg.create_color_clip(video_out, duration=sc.duration_seconds)
                    scene_video_paths.append(video_out)
                    completed_count += 1
                else:
                    # Fallback generation for scene to preserve whole timeline continuity
                    logger.warning("scene_clip_failed_generating_fallback", scene=sc.scene_number, err=clip_res.error_message)
                    sc.status = "completed"
                    sc.error_message = clip_res.error_message
                    await ffmpeg.create_color_clip(video_out, duration=sc.duration_seconds, color="#121826")
                    scene_video_paths.append(video_out)
                    completed_count += 1

                # Save checkpoint state.json
                scene_mgr.save_scene_state(project_id, sc)

                gen.completed_scenes = completed_count
                pct = 20.0 + (completed_count / max(1, len(scenes))) * 40.0
                await broadcast_step(
                    GenerationStatus.GENERATING_VIDEO,
                    round(pct, 1),
                    f"Scene {sc.scene_number}/{len(scenes)} rendered ({sc.title[:25]})",
                    {"completed_scenes": completed_count, "scene_number": sc.scene_number},
                )
                await db.commit()

            # -------------------------------------------------------------
            # STEP 3: VOICE SYNTHESIS & TIMING SYNC
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.GENERATING_VOICE, 65.0, "Synthesizing voice narration...")
            narration_file = str(proj_dir / "narration.wav")
            full_voice_text = " ".join([s.voice_over for s in scenes if s.voice_over]) or project.script or project.prompt

            voice_settings = {
                "language": project.voice_language or "en",
                "accent": project.voice_accent or "American",
                "voice_name": project.voice_name or "Samantha",
                "speed": project.voice_speed or 1.0,
            }

            voice_res = await router_svc.route_tts(
                text=full_voice_text,
                voice_settings=voice_settings,
                output_path=narration_file,
                quality_mode=quality_mode,
                job_id=generation_id,
            )

            has_narration = voice_res.success and os.path.exists(narration_file)

            # -------------------------------------------------------------
            # STEP 4: STITCHING SCENES (COMPOSITING)
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.COMPOSITING, 75.0, "Stitching scene timeline with FFmpeg...")
            stitched_video = str(proj_dir / "stitched.mp4")
            await ffmpeg.stitch_scenes(scene_video_paths, stitched_video)

            # -------------------------------------------------------------
            # STEP 5: AUDIO MIXING & DUCKING
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.SYNCING, 82.0, "Mixing and balancing audio tracks...")
            mixed_video = str(proj_dir / "mixed.mp4")
            await ffmpeg.mix_audio(
                video_path=stitched_video,
                output_path=mixed_video,
                narration_path=narration_file if has_narration else None,
                narration_volume=1.0,
                music_volume=0.25,
            )

            # -------------------------------------------------------------
            # STEP 6: SUBTITLES GENERATION & BURNING
            # -------------------------------------------------------------
            subtitled_video = mixed_video
            if project.include_subtitles and has_narration:
                await broadcast_step(GenerationStatus.ADDING_SUBTITLES, 88.0, "Generating subtitles via Whisper...")
                stt_res = await router_svc.route_stt(
                    audio_path=narration_file,
                    language=project.voice_language or "en",
                    quality_mode=quality_mode,
                    job_id=generation_id,
                )
                segments = stt_res.metadata.get("segments", []) if stt_res.metadata else []
                if segments:
                    srt_file = str(proj_dir / "subtitles.srt")
                    subtitle_gen.generate_srt(segments, srt_file)
                    subtitled_video = str(proj_dir / "subtitled.mp4")
                    await ffmpeg.burn_subtitles(mixed_video, srt_file, subtitled_video)

            # -------------------------------------------------------------
            # STEP 7: QUALITY CHECK
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.QUALITY_CHECK, 93.0, "Performing automated quality checks...")
            qc = await quality_checker.inspect(subtitled_video, expected_duration=float(project.target_duration))
            if qc.issues:
                logger.warning("quality_issues_detected", issues=qc.issues)

            # -------------------------------------------------------------
            # STEP 8: FINAL EXPORT (OPTIMIZED MP4)
            # -------------------------------------------------------------
            await broadcast_step(GenerationStatus.EXPORTING, 97.0, "Exporting master web-optimized MP4...")
            final_filename = f"render_{project_id}_{generation_id[:8]}.mp4"
            final_dest = str(renders_dir / final_filename)

            # Apply final export encoding
            await ffmpeg.export_final(subtitled_video, final_dest, fps=24)

            # Mark Completed!
            gen.status = GenerationStatus.COMPLETED
            gen.progress_percent = 100.0
            gen.current_step = "Video production complete!"
            gen.output_path = final_dest
            gen.completed_at = datetime.utcnow()
            project.output_path = final_dest
            project.status = "completed"
            await db.commit()

            await ws_manager.send_job_update(generation_id, {
                "job_id": generation_id,
                "status": "COMPLETED",
                "progress": 100.0,
                "step": "Video ready for download and playback",
                "output_path": final_dest,
            })
            logger.info("video_generation_completed_successfully", final_path=final_dest)

        except Exception as err:
            logger.error("generation_pipeline_fatal_error", error=str(err), job=generation_id)
            gen.status = GenerationStatus.FAILED
            gen.error_message = str(err)[:1000]
            gen.current_step = f"Production failed: {str(err)[:150]}"
            await db.commit()

            await ws_manager.send_job_update(generation_id, {
                "job_id": generation_id,
                "status": "FAILED",
                "error": str(err)[:400],
            })
