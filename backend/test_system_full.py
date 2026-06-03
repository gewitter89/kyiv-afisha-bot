"""
Full system test: checks imports, DB, publisher, crawler, Facebook parser, AI processor.
Run: python -X utf8 test_system_full.py
"""
import sys
import asyncio
sys.stdout.reconfigure(encoding='utf-8')

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(name, ok, detail=""):
    tag = PASS if ok else FAIL
    msg = f"{tag} {name}" + (f" — {detail}" if detail else "")
    print(msg)
    results.append((name, ok))

# ── 1. Core imports ────────────────────────────────────────────────────────────
print("\n=== 1. CORE IMPORTS ===")
try:
    from app.core.config import settings
    check("config.settings", True, f"AI_PROVIDER={settings.AI_PROVIDER}")
except Exception as e:
    check("config.settings", False, str(e))

try:
    from app.core.database import AsyncSessionLocal, engine
    check("database module", True)
except Exception as e:
    check("database module", False, str(e))

try:
    from app.models.models import Source, RawItem, Event, Post
    check("models import", True)
except Exception as e:
    check("models import", False, str(e))

# ── 2. Publisher ───────────────────────────────────────────────────────────────
print("\n=== 2. PUBLISHER ===")
try:
    from app.services.publisher import (
        format_single_event_card, send_telegram_message,
        _get_fallback_image, _format_datetime, FALLBACK_IMAGES, CAT_EMOJI
    )
    check("publisher imports", True)
    # Test fallback images
    for cat in ["concert", "theater", "party", "exhibition", "kids", "food", "other"]:
        img = _get_fallback_image(cat)
        check(f"fallback image [{cat}]", img is not None and img.startswith("http"), img[:50] if img else "None")
    # Test date formatter
    from datetime import datetime
    dt = datetime(2026, 7, 4, 20, 0)
    date_str = _format_datetime(dt)
    check("date formatter", "липня" in date_str or "07" in date_str, date_str)
    # Test emoji map
    check("emoji map complete", len(CAT_EMOJI) >= 10, f"{len(CAT_EMOJI)} categories")
except Exception as e:
    check("publisher", False, str(e))

# ── 3. Event card format test ──────────────────────────────────────────────────
print("\n=== 3. EVENT CARD FORMAT ===")
try:
    from app.services.publisher import format_single_event_card
    from app.models.models import Event
    from decimal import Decimal
    from datetime import datetime

    mock_event = Event()
    mock_event.title = "Океан Ельзи — Великий концерт"
    mock_event.category = "concert"
    mock_event.short_description = "Вони повертаються 🎸 Сет з 3 альбомів, живий звук, море емоцій."
    mock_event.start_datetime = datetime(2026, 7, 12, 20, 0)
    mock_event.venue_name = "Палац Спорту"
    mock_event.district = "Печерськ"
    mock_event.is_free = False
    mock_event.price_min = Decimal("350")
    mock_event.price_max = Decimal("2500")
    mock_event.price_text_original = None
    mock_event.date_text_original = None
    mock_event.ticket_url = "https://concert.ua/test"
    mock_event.source_url = "https://concert.ua/test"
    mock_event.source_name = "Concert.ua"
    mock_event.image_url = None

    card = asyncio.run(format_single_event_card(mock_event))
    check("event card generated", len(card) > 50, f"{len(card)} chars")
    check("card has title", "ОКЕАН ЕЛЬЗИ" in card.upper())
    check("card has HTML bold", "<b>" in card)
    check("card has date", "липня" in card or "07" in card or "12" in card)
    check("card has venue", "Палац" in card)
    check("card has price", "350" in card)
    check("card has separator", "━" in card)
    check("card has hashtag", "#" in card)
    # Safe preview — replace surrogate chars for Windows console
    preview = card[:400].encode('utf-16', 'surrogatepass').decode('utf-16')
    print(f"\n--- Sample card preview ---\n{preview}\n---")

except Exception as e:
    check("event card format", False, str(e))
    import traceback; traceback.print_exc()

# ── 4. Crawler / Generic Parser ───────────────────────────────────────────────
print("\n=== 4. CRAWLER MODULES ===")
try:
    from app.services.crawler.generic import GenericHtmlParser, _is_valid_image_url, _extract_best_image
    check("generic parser import", True)
    check("image validator — good url", _is_valid_image_url("https://cdn.example.com/event-poster.jpg"))
    check("image validator — logo skip", not _is_valid_image_url("https://cdn.example.com/logo.png"))
    check("image validator — data uri skip", not _is_valid_image_url("data:image/png;base64,abc"))
except Exception as e:
    check("generic parser", False, str(e))

try:
    from app.services.crawler.site_parsers import get_parser_for_url
    p = get_parser_for_url("https://kyiv.karabas.com/concert/test", 1, "Karabas")
    check("site parser factory", p is not None, type(p).__name__)
except Exception as e:
    check("site parser factory", False, str(e))

try:
    from app.services.crawler.rss import RssParser
    check("rss parser import", True)
except Exception as e:
    check("rss parser import", False, str(e))

# ── 5. Facebook Parser ────────────────────────────────────────────────────────
print("\n=== 5. FACEBOOK PARSER ===")
try:
    from app.services.crawler.facebook_parser import FacebookParser, crawl_facebook_source
    check("facebook_parser import", True)
    fb = FacebookParser(99, "TestPage", "kyivafisha", posts_count=1)
    check("FacebookParser instantiation", True, f"page=@{fb.page_username}")
except Exception as e:
    check("facebook_parser import", False, str(e))

try:
    import facebook_scraper
    check("facebook-scraper library installed", True, f"version={getattr(facebook_scraper, '__version__', 'unknown')}")
except ImportError:
    check("facebook-scraper library installed", False, "Run: pip install facebook-scraper")

# ── 6. AI Processor ───────────────────────────────────────────────────────────
print("\n=== 6. AI PROCESSOR ===")
try:
    from app.services.ai_processor import ai_processor, AIProcessor
    check("ai_processor import", True)
    check("provider configured", ai_processor.provider in ["openai", "deepseek", "mock"],
          f"provider={ai_processor.provider}")
    check("deepseek client ready", ai_processor.client is not None,
          "None — will use mock" if ai_processor.client is None else "connected")

    # Test mock rewrite (no API call)
    mock_data = {
        "title": "Тест концерт",
        "full_description": "Концерт у Києві",
        "category": "concert",
    }
    rewrite = asyncio.run(ai_processor._rewrite_via_mock(mock_data))
    check("mock rewrite works", len(rewrite) > 10, rewrite[:60])
except Exception as e:
    check("ai_processor", False, str(e))
    import traceback; traceback.print_exc()

# ── 7. Database connectivity ──────────────────────────────────────────────────
print("\n=== 7. DATABASE ===")
async def check_db():
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, text
    from app.models.models import Source, Event, RawItem, Post
    async with AsyncSessionLocal() as session:
        sources = (await session.execute(select(Source).where(Source.enabled == True))).scalars().all()
        events = (await session.execute(select(Event))).scalars().all()
        raw_items = (await session.execute(select(RawItem))).scalars().all()
        posts = (await session.execute(select(Post))).scalars().all()
        return len(sources), len(events), len(raw_items), len(posts)

try:
    ns, ne, nr, np_ = asyncio.run(check_db())
    check("DB connection", True)
    check("sources in DB", ns > 0, f"{ns} enabled sources")
    check("events in DB", ne >= 0, f"{ne} events total")
    check("raw_items in DB", nr >= 0, f"{nr} raw items")
    check("posts in DB", np_ >= 0, f"{np_} posts")
except Exception as e:
    check("database", False, str(e))
    import traceback; traceback.print_exc()

# ── 8. Worker / Celery tasks ──────────────────────────────────────────────────
print("\n=== 8. CELERY TASKS ===")
try:
    from app.tasks.worker import celery_app, crawl_source_task, process_raw_item_task
    check("celery_app import", True, f"broker={celery_app.conf.broker_url[:40]}...")
    check("crawl_source_task registered", crawl_source_task is not None)
    check("process_raw_item_task registered", process_raw_item_task is not None)
    scheduled = list(celery_app.conf.beat_schedule.keys())
    check("beat schedule loaded", len(scheduled) >= 4, f"{len(scheduled)} scheduled tasks")
except Exception as e:
    check("celery tasks", False, str(e))
    import traceback; traceback.print_exc()

# ── 9. Telegram Bot ───────────────────────────────────────────────────────────
print("\n=== 9. TELEGRAM CONFIG ===")
try:
    from app.core.config import settings
    check("BOT_TOKEN set", bool(settings.TELEGRAM_BOT_TOKEN), f"...{settings.TELEGRAM_BOT_TOKEN[-8:] if settings.TELEGRAM_BOT_TOKEN else 'EMPTY'}")
    check("CHANNEL_ID set", bool(settings.TELEGRAM_CHANNEL_ID), settings.TELEGRAM_CHANNEL_ID or "EMPTY")
    check("DEEPSEEK_KEY set", bool(settings.DEEPSEEK_API_KEY), f"...{settings.DEEPSEEK_API_KEY[-6:] if settings.DEEPSEEK_API_KEY else 'EMPTY'}")
    check("FB_EMAIL set", bool(settings.FACEBOOK_EMAIL), settings.FACEBOOK_EMAIL or "EMPTY")
    check("FB_PASSWORD set", bool(settings.FACEBOOK_PASSWORD), "***" if settings.FACEBOOK_PASSWORD else "EMPTY")
    check("AUTO_PUBLISH", settings.AUTO_PUBLISH, str(settings.AUTO_PUBLISH))
    check("MIN_SCORE", True, str(getattr(settings, 'AUTO_PUBLISH_MIN_SCORE', 65)))
    check("MAX_POSTS_DAY", True, str(getattr(settings, 'MAX_POSTS_PER_DAY', 8)))
except Exception as e:
    check("telegram config", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "="*50)
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(results)} checks")
if failed == 0:
    print("ALL SYSTEMS GO!")
else:
    print("FAILED CHECKS:")
    for name, ok in results:
        if not ok:
            print(f"  - {name}")
