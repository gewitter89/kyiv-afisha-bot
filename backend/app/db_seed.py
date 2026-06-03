import asyncio
import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.models import Category, Source, AdminUser, Base
from app.core.security import get_password_hash
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_seed")

CATEGORIES = [
    {"slug": "today", "name": "Сьогодні"},
    {"slug": "weekend", "name": "Вихідні"},
    {"slug": "concert", "name": "Концерти"},
    {"slug": "theater", "name": "Театр"},
    {"slug": "standup", "name": "Стендап"},
    {"slug": "exhibition", "name": "Виставки"},
    {"slug": "party", "name": "Вечірки"},
    {"slug": "food", "name": "Їжа"},
    {"slug": "bar", "name": "Бари"},
    {"slug": "restaurant", "name": "Ресторани"},
    {"slug": "kids", "name": "Дітям"},
    {"slug": "family", "name": "Сімейний відпочинок"},
    {"slug": "date", "name": "Для побачень"},
    {"slug": "free", "name": "Безкоштовно"},
    {"slug": "sport", "name": "Спорт"},
    {"slug": "workshop", "name": "Воркшопи"},
    {"slug": "cinema", "name": "Кіно"},
    {"slug": "lecture", "name": "Лекції"},
    {"slug": "unusual", "name": "Незвичайні події"},
    {"slug": "tourist", "name": "Для туристів"},
    {"slug": "news", "name": "Новини"},
    {"slug": "other", "name": "Інше"},
]

DEMO_SOURCES = [
    # --- RSS / Feed Sources ---
    {
        "name": "Vgorode Kyiv RSS (Новини та Події)",
        "type": "rss",
        "url": "https://kiev.vgorode.ua/xml/rss.xml",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Moe Misto Kyiv RSS (Афіша)",
        "type": "rss",
        "url": "https://moemisto.ua/kiev/rss",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Gloss.ua RSS (Гід подій)",
        "type": "rss",
        "url": "https://gloss.ua/xml/rss.xml",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Weekend.today RSS (Куди піти)",
        "type": "rss",
        "url": "https://weekend.today/rss",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Platfor.ma RSS (Лекції та Воркшопи)",
        "type": "rss",
        "url": "https://platfor.ma/events/rss",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Наш Київ RSS (Новини та події міста)",
        "type": "rss",
        "url": "https://nashkiev.ua/feed",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "The Village Україна RSS (Життя та культура Києва)",
        "type": "rss",
        "url": "https://www.the-village.com.ua/feed",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "БЖ RSS (Нові заклади, їжа та міська культура)",
        "type": "rss",
        "url": "https://bzh.life/feed/",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Хмарочос RSS (Урбаністика та події)",
        "type": "rss",
        "url": "https://hmarochos.kiev.ua/feed/",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "RestOn RSS (Ресторанний гід Києва)",
        "type": "rss",
        "url": "https://reston.ua/ru/blog/rss",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Kyiv Post RSS (English-language events & news)",
        "type": "rss",
        "url": "https://www.kyivpost.com/rss",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    
    # --- Website Aggregators & Tickets ---
    {
        "name": "Kyivmaps (Події та Локації)",
        "type": "website",
        "url": "https://kyivmaps.com/events",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Concert.ua (Квитки на концерти)",
        "type": "website",
        "url": "https://concert.ua/uk/kyiv",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Pokupon Kyiv (Знижки та Купони)",
        "type": "website",
        "url": "https://pokupon.ua/kiev/razvlecheniya",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Kontramarka Kyiv (Театр та Концерти)",
        "type": "website",
        "url": "https://kontramarka.ua/uk/kyiv",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "TicketsBox Kyiv (Афіша та квитки)",
        "type": "website",
        "url": "https://ticketsbox.com/kyiv/",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Karabas Kyiv (Квиткова каса)",
        "type": "website",
        "url": "https://karabas.com/ua/r/kyiv/",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Superdeal Kyiv (Знижки на розваги)",
        "type": "website",
        "url": "https://superdeal.ua/kiev/razvlecheniya",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Gastroli.ua (Квитки на концерти в Києві)",
        "type": "website",
        "url": "https://gastroli.ua/city/kiev",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Parter.ua (Театральна каса та концерти)",
        "type": "website",
        "url": "https://parter.ua/",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Soldout.ua (Концерти та вистави)",
        "type": "website",
        "url": "https://soldout.ua/",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    {
        "name": "Kasa.in.ua (Квитки на події)",
        "type": "website",
        "url": "https://kasa.in.ua/",
        "enabled": False,
        "crawl_interval_minutes": 60,
    },
    
    # --- Telegram Channels (Monitors) ---
    {
        "name": "Афіша Києва",
        "type": "telegram",
        "telegram_channel_username": "kyiv_afisha",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Куди піти? Київ",
        "type": "telegram",
        "telegram_channel_username": "kuda_piti_kiev",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Київ Зараз",
        "type": "telegram",
        "telegram_channel_username": "kiev_now",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Київ Гід",
        "type": "telegram",
        "telegram_channel_username": "kyivguide",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Культурний Київ",
        "type": "telegram",
        "telegram_channel_username": "culture_kyiv",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Стендап Київ",
        "type": "telegram",
        "telegram_channel_username": "standup_kyiv",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Діти Київ (Сімейне дозвілля)",
        "type": "telegram",
        "telegram_channel_username": "kids_kyiv",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Афіша Києва - Заходи",
        "type": "telegram",
        "telegram_channel_username": "afishakieva",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Kyivmaps події",
        "type": "telegram",
        "telegram_channel_username": "kyivmaps",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "БЖ - Більше Життя",
        "type": "telegram",
        "telegram_channel_username": "bzh_life",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "The Village Україна",
        "type": "telegram",
        "telegram_channel_username": "thevillageua",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Наш Київ новини",
        "type": "telegram",
        "telegram_channel_username": "nashkyiv",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Київська Халява (Безкоштовні події та знижки)",
        "type": "telegram",
        "telegram_channel_username": "kyiv_halyava",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Стендап Афіша Києва",
        "type": "telegram",
        "telegram_channel_username": "standup_kyiv_afisha",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Київ Їжа та Бари - рекомендації",
        "type": "telegram",
        "telegram_channel_username": "kyiv_food",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Куди піти на вихідних",
        "type": "telegram",
        "telegram_channel_username": "kiev_weekend",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Київ Афіша Канал",
        "type": "telegram",
        "telegram_channel_username": "kiev_afisha_channel",
        "enabled": False,
        "crawl_interval_minutes": 30,
    },
    {
        "name": "Дитячий Київ",
        "type": "telegram",
        "telegram_channel_username": "kiev_deti",
        "enabled": False,
        "crawl_interval_minutes": 30,
    }
]

async def seed_data():
    global engine, AsyncSessionLocal
    
    try:
        # Test connection to Postgres
        async with engine.connect() as conn:
            await conn.execute(select(1))
    except Exception as e:
        # Fallback to SQLite
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        import app.core.database
        
        sqlite_engine = create_async_engine(
            "sqlite+aiosqlite:///test_kyiv_events.db",
            echo=False,
            future=True
        )
        sqlite_sessionmaker = async_sessionmaker(
            bind=sqlite_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        app.core.database.engine = sqlite_engine
        app.core.database.AsyncSessionLocal = sqlite_sessionmaker
        
        engine = sqlite_engine
        AsyncSessionLocal = sqlite_sessionmaker

    async with AsyncSessionLocal() as session:
        # Create all tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # 1. Seed admin user
        logger.info("Checking for admin user...")
        admin_q = await session.execute(select(AdminUser).where(AdminUser.email == settings.ADMIN_EMAIL))
        admin = admin_q.scalar_one_or_none()
        
        if not admin:
            logger.info(f"Creating admin user: {settings.ADMIN_EMAIL}")
            admin = AdminUser(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin"
            )
            session.add(admin)
        else:
            logger.info("Admin user already exists.")

        # 2. Seed Categories
        logger.info("Seeding categories...")
        for cat_data in CATEGORIES:
            cat_q = await session.execute(select(Category).where(Category.slug == cat_data["slug"]))
            cat = cat_q.scalar_one_or_none()
            if not cat:
                logger.info(f"Adding category: {cat_data['name']}")
                cat = Category(slug=cat_data["slug"], name=cat_data["name"])
                session.add(cat)

        # 3. Seed Sources
        logger.info("Seeding demo sources...")
        for src_data in DEMO_SOURCES:
            src_q = await session.execute(
                select(Source).where(
                    (Source.name == src_data["name"]) | 
                    (Source.url == src_data["url"]) if src_data.get("url") else False
                )
            )
            src = src_q.scalar_one_or_none()
            if not src:
                logger.info(f"Adding source: {src_data['name']}")
                src = Source(
                    name=src_data["name"],
                    type=src_data["type"],
                    url=src_data.get("url"),
                    telegram_channel_username=src_data.get("telegram_channel_username"),
                    enabled=src_data["enabled"],
                    crawl_interval_minutes=src_data["crawl_interval_minutes"]
                )
                session.add(src)

        await session.commit()
        logger.info("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
