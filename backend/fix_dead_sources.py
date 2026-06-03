"""
Скрипт для исправления мёртвых URL источников и отключения нерабочих.
Запуск: python fix_dead_sources.py
"""
import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.models import Source

# Маппинг: старый URL → новый URL (или None = отключить источник)
URL_FIXES = {
    # Multiplex — изменился URL
    "https://multiplex.ua/ua/city/kyiv/movies": "https://multiplex.ua/ua/kyiv/",
    # Planeta Kino — изменился URL
    "https://planetakino.ua/ua/kyiv/": "https://planetakino.com.ua/ua/kyiv/",
    # Eda.ua — изменился формат
    "https://eda.ua/kyiv/restaurants/": None,  # отключить
    # GoToShop — 403, блокирует ботов
    "https://gotoshop.ua/kyiv/": None,  # отключить
    # Boxing in Kyiv — DNS не резолвится
    "https://palats-sportu.com.ua/events/": None,  # отключить
    # Dynamo Kyiv — DNS не резолвится
    "https://www.tcdynamo.kyiv.ua/uk/matches/calendar/": None,  # отключить
}

async def fix_sources():
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Source))
        sources = q.scalars().all()
        
        fixed = 0
        disabled = 0
        
        for source in sources:
            if not source.url:
                continue
            for old_url, new_url in URL_FIXES.items():
                if old_url in (source.url or ""):
                    if new_url is None:
                        source.enabled = False
                        print(f"❌ Отключён: {source.name} ({source.url})")
                        disabled += 1
                    else:
                        source.url = new_url
                        print(f"✅ Исправлен: {source.name} → {new_url}")
                        fixed += 1
                    break
        
        await session.commit()
        print(f"\n✅ Готово! Исправлено: {fixed}, Отключено: {disabled}")

asyncio.run(fix_sources())
