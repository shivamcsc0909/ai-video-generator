"""
Celery application instance and configuration.

Workers are started with:
    celery -A backend.core.celery_app worker -Q generation,media,default -c 2
"""

from __future__ import annotations

from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

# ------------------------------------------------------------------ #
# Application
# ------------------------------------------------------------------ #
celery_app = Celery(
    "aivideo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.workers.pipeline_tasks"],
)

# ------------------------------------------------------------------ #
# Configuration
# ------------------------------------------------------------------ #
celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Results
    result_expires=86_400,  # 24 h
    result_extended=True,
    # Execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Concurrency cap (can be overridden via CLI -c flag)
    worker_max_tasks_per_child=50,
    # Retries
    task_max_retries=3,
    task_default_retry_delay=30,
    # Routes
    task_routes={
        # Heavy generation tasks → dedicated queue with GPU workers
        "backend.workers.pipeline_tasks.run_full_pipeline": {"queue": "generation"},
        "backend.workers.pipeline_tasks.generate_scene_image": {"queue": "generation"},
        "backend.workers.pipeline_tasks.generate_scene_video": {"queue": "generation"},
        # Media post-processing tasks → separate queue
        "backend.workers.pipeline_tasks.generate_voice_over": {"queue": "media"},
        "backend.workers.pipeline_tasks.composite_final_video": {"queue": "media"},
        "backend.workers.pipeline_tasks.add_subtitles": {"queue": "media"},
        # Lightweight / orchestration tasks → default queue
        "backend.workers.pipeline_tasks.analyze_prompt": {"queue": "default"},
        "backend.workers.pipeline_tasks.generate_storyboard": {"queue": "default"},
        "backend.workers.pipeline_tasks.quality_check": {"queue": "default"},
    },
    # Beat schedule (if celery beat is used for periodic tasks)
    beat_schedule={},
)
