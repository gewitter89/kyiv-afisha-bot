import logging
from app.tasks.jobs import crawl_all_sources_by_type_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trigger_crawls")

def trigger_all():
    logger.info("Triggering RSS crawl task...")
    crawl_all_sources_by_type_task.delay("rss")
    
    logger.info("Triggering Telegram channels crawl task...")
    crawl_all_sources_by_type_task.delay("telegram")
    
    logger.info("Triggering Website crawl task...")
    crawl_all_sources_by_type_task.delay("website")
    
    logger.info("Successfully queued all crawls! The Celery worker will process them immediately.")

if __name__ == "__main__":
    trigger_all()
