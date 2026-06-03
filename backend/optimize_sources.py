import asyncio
import logging
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.models.models import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("optimize_sources")

async def optimize():
    logger.info("Optimizing crawler sources in database...")
    async with AsyncSessionLocal() as session:
        # 1. Update ticket sites to correct, active URLs
        logger.info("Updating ticket sites URLs...")
        
        # Karabas Subdomain
        await session.execute(
            update(Source)
            .where(Source.name.like("%Karabas%"))
            .values(url="https://kyiv.karabas.com/")
        )
        
        # TicketsBox Subdomain
        await session.execute(
            update(Source)
            .where(Source.name.like("%TicketsBox%"))
            .values(url="https://kyiv.ticketsbox.com/")
        )
        
        # Kontramarka Root
        await session.execute(
            update(Source)
            .where(Source.name.like("%Kontramarka%"))
            .values(url="https://kontramarka.ua/")
        )
        
        # Gastroli Root
        await session.execute(
            update(Source)
            .where(Source.name.like("%Gastroli%"))
            .values(url="https://gastroli.ua/")
        )
        
        # 2. Disable dead/obsolete RSS feeds to prevent log pollution (we crawl them via Telegram channels)
        logger.info("Disabling dead RSS feeds...")
        dead_rss_sources = [
            "Kyiv Post RSS",
            "RestOn RSS",
            "БЖ RSS",
            "The Village Україна RSS",
            "Наш Київ RSS",
            "Gloss.ua RSS",
            "Vgorode Kyiv RSS",
            "Moe Misto Kyiv RSS"
        ]
        
        for name in dead_rss_sources:
            await session.execute(
                update(Source)
                .where((Source.name.like(f"%{name}%")) & (Source.type == "rss"))
                .values(enabled=False)
            )
            
        await session.commit()
        logger.info("Database optimization completed successfully!")

if __name__ == "__main__":
    asyncio.run(optimize())
