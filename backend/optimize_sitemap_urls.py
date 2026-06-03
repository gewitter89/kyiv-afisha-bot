import asyncio
import logging
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.models.models import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("optimize_sitemap_urls")

async def run_update():
    logger.info("Updating website sources to use XML sitemaps...")
    async with AsyncSessionLocal() as session:
        # Kyivmaps
        await session.execute(
            update(Source)
            .where(Source.name.like("%Kyivmaps%") & (Source.type == "website"))
            .values(url="https://kyivmaps.com/sitemap.xml")
        )
        
        # Pokupon
        await session.execute(
            update(Source)
            .where(Source.name.like("%Pokupon%") & (Source.type == "website"))
            .values(url="https://pokupon.ua/aktsii.xml")
        )
        
        # Superdeal
        await session.execute(
            update(Source)
            .where(Source.name.like("%Superdeal%") & (Source.type == "website"))
            .values(url="https://superdeal.ua/aktsii.xml")
        )
        
        # Soldout
        await session.execute(
            update(Source)
            .where(Source.name.like("%Soldout%") & (Source.type == "website"))
            .values(url="https://soldout.ua/sitemap/events.xml")
        )
        
        await session.commit()
        logger.info("Sitemap URLs updated in database successfully!")

if __name__ == "__main__":
    asyncio.run(run_update())
