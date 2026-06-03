import asyncio
import os
import sys
from datetime import datetime
from sqlalchemy import select

# Add current folder to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
import app.core.database
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.models import Source, RawItem, Event
from app.services.ai_processor import ai_processor
from app.services.deduplicator import process_event_deduplication
from app.services.publisher import publish_single_event

def safe_print(text: str):
    """
    Safely prints text on Windows console by encoding to terminal's stdout encoding or ignoring emojis.
    """
    try:
        # Try to print normally
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode and decode with ignore to strip non-encodable chars (emojis)
        try:
            enc = sys.stdout.encoding or 'utf-8'
            print(text.encode(enc, errors='ignore').decode(enc))
        except Exception:
            # Fallback to ascii representation
            print(text.encode('ascii', errors='ignore').decode('ascii'))

async def main():
    # Disable AUTO_PUBLISH for the test runner to keep verification steps discrete
    settings.AUTO_PUBLISH = False
    
    safe_print("=" * 75)
    safe_print("[START] STARTING KYIV EVENT GUIDE PIPELINE TEST RUN [START]")
    safe_print("=" * 75)
    
    # 1. Initialize Tables
    safe_print("\nStep 1: Initializing database connection...")
    global engine, AsyncSessionLocal
    
    try:
        # Test connection to Postgres
        async with engine.connect() as conn:
            await conn.execute(select(1))
        safe_print("[OK] Connected to Postgres database.")
    except Exception as e:
        safe_print(f"[WARN] Postgres connection failed ({e}).")
        safe_print("[INFO] Switching to local SQLite database (test_kyiv_events.db) for this test run...")
        
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        
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
        
        # Patch the database module so other services use SQLite
        app.core.database.engine = sqlite_engine
        app.core.database.AsyncSessionLocal = sqlite_sessionmaker
        
        engine = sqlite_engine
        AsyncSessionLocal = sqlite_sessionmaker

    # Create tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        safe_print("[OK] Database tables created/checked successfully.")
    except Exception as e:
        safe_print(f"[ERROR] Database initialization failed: {e}")
        return

    # 2. Setup a Demo Source
    safe_print("\nStep 2: Creating test source in DB...")
    source_id = 999
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Source).where(Source.id == source_id))
        source = q.scalar_one_or_none()
        if not source:
            source = Source(
                id=source_id,
                name="Test Source (Mock Scraper)",
                type="website",
                url="https://concert.ua/uk/kyiv",
                enabled=True,
                crawl_interval_minutes=60
            )
            session.add(source)
            await session.commit()
            safe_print("[OK] Test source created in database.")
        else:
            safe_print("[OK] Test source already exists.")

    # 3. Simulate a Raw crawled item
    safe_print("\nStep 3: Simulating a raw crawled event post...")
    raw_text = (
        "🎷 Великий Джазовий Вечір на Даху ЦУМу!\n\n"
        "15 червня о 19:00 відбудеться найочікуваніша подія сезону. "
        "Класичні джазові стандарти у виконанні найкращих джазменів Києва. "
        "Подія пройде на чудовому даху ЦУМу з видом на Хрещатик. "
        "Адреса: вул. Хрещатик, 38, Київ.\n"
        "Ціна квитків: від 350 до 800 грн.\n"
        "Вхід тільки за квитками. Придбати квитки можна за посиланням: "
        "https://concert.ua/uk/event/jazz-on-tsum-rooftop\n"
        "Організатор: Kyiv Jazz Alliance."
    )
    # Using a beautiful public picture of a jazz concert
    image_url = "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=800"
    
    from app.core.security import compute_raw_item_hash
    item_hash = compute_raw_item_hash(raw_text, "https://concert.ua/uk/event/jazz-on-tsum-rooftop")
    
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(RawItem).where(RawItem.hash == item_hash))
        raw_item = q.scalar_one_or_none()
        if not raw_item:
            raw_item = RawItem(
                source_id=source_id,
                external_id="test_raw_item_999",
                url="https://concert.ua/uk/event/jazz-on-tsum-rooftop",
                title="Джазовий Вечір на Даху ЦУМу",
                raw_text=raw_text,
                image_url=image_url,
                published_at=datetime.utcnow(),
                fetched_at=datetime.utcnow(),
                hash=item_hash,
                processing_status="new"
            )
            session.add(raw_item)
            await session.commit()
            safe_print(f"[OK] Raw item created in DB (ID: {raw_item.id}).")
        else:
            safe_print(f"[OK] Raw item already exists in DB (ID: {raw_item.id}).")
            # Reset processing status so we run the extraction
            raw_item.processing_status = "new"
            raw_item.error_message = None
            await session.commit()

    # 4. Process Raw Item through AI / Fallback Extraction
    safe_print("\nStep 4: Processing raw item through AI/Mock extraction and formatting...")
    from app.tasks.jobs import process_raw_item_job
    await process_raw_item_job(raw_item.id)
    
    # Query the generated Event
    async with AsyncSessionLocal() as session:
        q_ev = await session.execute(
            select(Event).where(Event.source_url == "https://concert.ua/uk/event/jazz-on-tsum-rooftop")
        )
        event = q_ev.scalars().first()
        
    if not event:
        safe_print("[ERROR] Failed to process raw item: Event was not generated.")
        # Check if there is an error in raw item
        async with AsyncSessionLocal() as session:
            q_raw = await session.execute(select(RawItem).where(RawItem.id == raw_item.id))
            r = q_raw.scalar_one()
            safe_print(f"   - RawItem status: {r.processing_status}")
            safe_print(f"   - Error message: {r.error_message}")
        return
        
    safe_print(f"[OK] Event generated successfully!")
    safe_print(f"   - Title: {event.title}")
    safe_print(f"   - Category: {event.category}")
    safe_print(f"   - Venue: {event.venue_name}")
    safe_print(f"   - Date Text: {event.date_text_original}")
    safe_print(f"   - Start datetime: {event.start_datetime}")
    safe_print(f"   - Price Text: {event.price_text_original}")
    safe_print(f"   - Minimum price: {event.price_min} UAH")
    safe_print(f"   - Quality Score: {event.quality_score}/100")
    safe_print(f"   - Moderation Status: {event.status}")
    safe_print(f"   - Generated Telegram Post content:\n")
    safe_print(f"--------------------------------------------------")
    safe_print(event.short_description)
    safe_print(f"--------------------------------------------------")

    # 5. Publish to Telegram Channel
    safe_print("\nStep 5: Attempting to publish to Telegram Channel...")
    safe_print(f"   - Token: {settings.TELEGRAM_BOT_TOKEN[:15]}... (length: {len(settings.TELEGRAM_BOT_TOKEN)})")
    safe_print(f"   - Channel ID: {settings.TELEGRAM_CHANNEL_ID}")
    
    async with AsyncSessionLocal() as session:
        # Merge event to keep track in session
        event = await session.merge(event)
        success, err = await publish_single_event(event, session)
        
    if success:
        safe_print("\n[SUCCESS] The event has been successfully published to your channel with media.")
        safe_print(f"   - Published to Telegram At: {event.published_to_telegram_at}")
        safe_print(f"   - Current Event Status: {event.status}")
    else:
        safe_print(f"\n[ERROR] Telegram Channel Publication Failed: {err}")
        safe_print("[INFO] Tip: Make sure your bot is added to the channel as an Administrator with 'Post Messages' permission.")

    safe_print("\n" + "=" * 75)
    safe_print("[END] PIPELINE TEST COMPLETED [END]")
    safe_print("=" * 75)

if __name__ == "__main__":
    asyncio.run(main())
