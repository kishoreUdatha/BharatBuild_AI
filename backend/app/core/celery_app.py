from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "bharatbuild",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.modules.projects.tasks",
        "app.modules.builds.tasks",
    ]
)

# Configure Celery for reliability and load handling
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,

    # Timeouts
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit

    # Result storage
    result_expires=86400,  # 24 hours

    # Worker configuration for load handling
    worker_prefetch_multiplier=1,  # Fetch 1 task at a time (prevents task hoarding)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory cleanup)
    worker_max_memory_per_child=512000,  # Restart if memory exceeds 512MB

    # Connection reliability
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Task reliability settings
    task_acks_late=True,  # Acknowledge after task completes (prevents lost tasks)
    task_reject_on_worker_lost=True,  # Requeue task if worker dies
    task_acks_on_failure_or_timeout=False,  # Don't ack failed tasks (allow retry)

    # Retry settings (global defaults)
    task_default_retry_delay=30,  # 30 seconds default retry delay
    task_publish_retry=True,  # Retry publishing to broker
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0.5,
        'interval_step': 0.5,
        'interval_max': 3,
    },

    # Queue settings for load balancing
    task_default_queue='default',
    task_create_missing_queues=True,
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Add periodic tasks here when needed
}
