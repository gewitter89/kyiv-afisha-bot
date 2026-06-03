import os
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Initialize Celery app with SQLite fallback if Redis is not configured or offline
if settings.REDIS_URL and settings.REDIS_URL.startswith("redis://"):
    broker_url = settings.REDIS_URL
    backend_url = settings.REDIS_URL
else:
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    broker_path = os.path.join(base_dir, 'celery_broker.db').replace('\\', '/')
    results_path = os.path.join(base_dir, 'celery_results.db').replace('\\', '/')
    broker_url = f"sqla+sqlite:///{broker_path}"
    backend_url = f"db+sqlite:///{results_path}"

celery_app = Celery(
    "kyiv-event-guide-tasks",
    broker=broker_url,
    backend=backend_url
)

# Standard Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Kiev",
    enable_utc=True,
    imports=(
        "app.tasks.worker",
        "app.tasks.jobs",
    )
)

# Celery Beat Scheduler Configuration
celery_app.conf.beat_schedule = {
    # 1. RSS Crawl: check every 30 minutes
    "crawl-rss-sources-every-30m": {
        "task": "app.tasks.jobs.crawl_all_sources_by_type_task",
        "schedule": 1800.0, # 30 minutes in seconds
        "args": ("rss",)
    },
    # 2. Website Crawl: check every 60 minutes
    "crawl-website-sources-every-60m": {
        "task": "app.tasks.jobs.crawl_all_sources_by_type_task",
        "schedule": 3600.0, # 60 minutes in seconds
        "args": ("website",)
    },
    # 3. Telegram Crawl: check every 30 minutes
    "crawl-telegram-sources-every-30m": {
        "task": "app.tasks.jobs.crawl_all_sources_by_type_task",
        "schedule": 1800.0,
        "args": ("telegram",)
    },
    # 4. Publish Scheduled Posts: check every 1 minute
    "publish-scheduled-posts-every-1m": {
        "task": "app.tasks.jobs.publish_scheduled_posts_task",
        "schedule": 60.0,
    },
    # 5. Daily Digest: every day at 08:00 AM Kyiv time (05:00/06:00 UTC)
    "generate-daily-digest-today": {
        "task": "app.tasks.jobs.run_daily_digest_task",
        "schedule": crontab(hour=8, minute=0)
    },
    # 6. Tomorrow Digest: every day at 18:00 (6:00 PM Kyiv time)
    "generate-daily-digest-tomorrow": {
        "task": "app.tasks.jobs.run_tomorrow_digest_task",
        "schedule": crontab(hour=18, minute=0)
    },
    # 7. Weekend Digest: Thursday at 18:00 (6:00 PM Kyiv time)
    "generate-weekend-digest": {
        "task": "app.tasks.jobs.run_weekend_digest_task",
        "schedule": crontab(day_of_week=4, hour=18, minute=0)
    },
    # 8. Archive Past Events: every night at 02:00 AM Kyiv time
    "archive-past-events-daily": {
        "task": "app.tasks.jobs.archive_past_events_task",
        "schedule": crontab(hour=2, minute=0)
    }
}

# Shortcut to access the task runner
@celery_app.task(name="app.tasks.worker.crawl_source_task")
def crawl_source_task(source_id: int):
    # Dynamically resolve import to prevent circularity
    from app.tasks.jobs import crawl_source_job
    import asyncio
    asyncio.run(crawl_source_job(source_id))

@celery_app.task(name="app.tasks.worker.process_raw_item_task")
def process_raw_item_task(raw_item_id: int):
    from app.tasks.jobs import process_raw_item_job
    import asyncio
    asyncio.run(process_raw_item_job(raw_item_id))
