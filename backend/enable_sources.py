import asyncio
import logging
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.models.models import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enable_sources")

async def enable_all_sources():
    logger.info("Connecting to database and enabling all crawl sources...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(update(Source).values(enabled=True))
        await session.commit()
        logger.info(f"Successfully enabled all sources! Affected rows: {result.rowcount}")

if __name__ == "__main__":
    asyncio.run(enable_all_sources())
