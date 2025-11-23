from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "bharatbuild",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.modules.projects.tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    result_expires=86400,  # 24 hours
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,  # Fix for Celery 6.0+ deprecation warning
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Add periodic tasks here when needed
}
