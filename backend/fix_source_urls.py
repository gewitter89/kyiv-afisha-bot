import asyncio
import logging
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.models import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_source_urls")

async def fix_urls():
    logger.info("Updating outdated source URLs in database...")
    async with AsyncSessionLocal() as session:
        # 1. Update Gastroli.ua
        await session.execute(
            update(Source)
            .where(Source.name.like("%Gastroli.ua%"))
            .values(url="https://gastroli.ua/")
        )
        
        # 2. Update Karabas
        await session.execute(
            update(Source)
            .where(Source.name.like("%Karabas%"))
            .values(url="https://karabas.com/ua/kyiv/")
        )
        
        # 3. Update TicketsBox
        await session.execute(
            update(Source)
            .where(Source.name.like("%TicketsBox%"))
            .values(url="https://ticketsbox.com/en/kyiv/")
        )
        
        await session.commit()
        logger.info("Outdated source URLs updated successfully!")

if __name__ == "__main__":
    asyncio.run(fix_urls())
