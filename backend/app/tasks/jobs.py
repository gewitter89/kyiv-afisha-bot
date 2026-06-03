import asyncio
import logging
import traceback
from datetime import datetime, timedelta, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sqlalchemy import select, and_, update, or_
from decimal import Decimal

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Source, RawItem, Event, EventSource, Post
from app.core.security import compute_raw_item_hash
from app.services.crawler.rss import RssParser
from app.services.crawler.tg_monitor import TelegramMonitor
from app.services.crawler.site_parsers import get_parser_for_url
from app.services.ai_processor import ai_processor
from app.services.deduplicator import process_event_deduplication
from app.services.publisher import send_telegram_message, publish_single_event, generate_and_publish_daily_digest, generate_and_publish_weekend_digest
from app.tasks.worker import celery_app

logger = logging.getLogger("jobs")

# --- CELERY BEAT JOBS ---

@celery_app.task(name="app.tasks.jobs.crawl_all_sources_by_type_task")
def crawl_all_sources_by_type_task(source_type: str):
    async def run():
        async with AsyncSessionLocal() as session:
            q = await session.execute(
                select(Source.id).where(
                    and_(Source.type == source_type, Source.enabled == True)
                )
            )
            source_ids = q.scalars().all()
            
        from app.tasks.worker import crawl_source_task
        for source_id in source_ids:
            crawl_source_task.delay(source_id)
            
    asyncio.run(run())

@celery_app.task(name="app.tasks.jobs.publish_scheduled_posts_task")
def publish_scheduled_posts_task():
    async def run():
        async with AsyncSessionLocal() as session:
            now = datetime.utcnow()
            q = await session.execute(
                select(Post).where(
                    and_(Post.status == "scheduled", Post.scheduled_at <= now)
                )
            )
            posts = q.scalars().all()
            
            for post in posts:
                logger.info(f"Publishing scheduled post ID {post.id}...")
                success, msg_id, err = await send_telegram_message(post.text)
                if success:
                    post.status = "published"
                    post.published_at = datetime.utcnow()
                    post.telegram_message_id = msg_id
                    # If this was tied to an event, mark event as published
                    if post.event_id:
                        q_ev = await session.execute(select(Event).where(Event.id == post.event_id))
                        ev = q_ev.scalar_one_or_none()
                        if ev:
                            ev.status = "published"
                            ev.published_to_telegram_at = datetime.utcnow()
                else:
                    post.status = "failed"
                    post.error_message = err
            await session.commit()
            
    asyncio.run(run())

@celery_app.task(name="app.tasks.jobs.run_daily_digest_task")
def run_daily_digest_task():
    async def run():
        async with AsyncSessionLocal() as session:
            await generate_and_publish_daily_digest(session)
    asyncio.run(run())

@celery_app.task(name="app.tasks.jobs.run_tomorrow_digest_task")
def run_tomorrow_digest_task():
    async def run():
        async with AsyncSessionLocal() as session:
            await generate_and_publish_daily_digest(session, for_tomorrow=True)
    asyncio.run(run())

@celery_app.task(name="app.tasks.jobs.run_weekend_digest_task")
def run_weekend_digest_task():
    async def run():
        async with AsyncSessionLocal() as session:
            await generate_and_publish_weekend_digest(session)
    asyncio.run(run())

@celery_app.task(name="app.tasks.jobs.run_facebook_promotion_task")
def run_facebook_promotion_task():
    async def run():
        import os
        from app.services.facebook_agent import generate_facebook_promo_text, run_fb_promotion
        
        groups_str = settings.FB_TARGET_GROUPS or ""
        if groups_str:
            group_urls = [g.strip() for g in groups_str.split(",") if g.strip()]
        else:
            group_urls = [
                "https://www.facebook.com/groups/kyiv.events", 
                "https://www.facebook.com/groups/kiev.afisha"
            ]
        
        async with AsyncSessionLocal() as session:
            text = await generate_facebook_promo_text(session)
            
        logger.info("Starting Celery Facebook promotion task...")
        success = await run_fb_promotion(group_urls, text)
        if success:
            logger.info("Facebook promotion task completed successfully.")
        else:
            logger.error("Facebook promotion task failed.")
            
    asyncio.run(run())

@celery_app.task(name="app.tasks.jobs.archive_past_events_task")
def archive_past_events_task():
    async def run():
        async with AsyncSessionLocal() as session:
            yesterday = datetime.utcnow() - timedelta(days=1)
            # Update status to archived for events that are past
            await session.execute(
                update(Event).where(
                    and_(
                        Event.status.in_(["approved", "published", "draft", "needs_review"]),
                        Event.end_datetime < yesterday if Event.end_datetime else Event.start_datetime < yesterday
                    )
                ).values(status="archived")
            )
            await session.commit()
            logger.info("Archived past events successfully.")
            
    asyncio.run(run())


# --- WORKER JOBS IMPLEMENTATION ---

async def crawl_source_job(source_id: int):
    """
    Crawls a single data source: RSS, website, Telegram, or Facebook.
    """
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Source).where(Source.id == source_id))
        source = q.scalar_one_or_none()
        if not source or not source.enabled:
            return
            
    try:
        if source.type == "rss":
            parser = RssParser(source.id, source.name, source.url)
            await parser.parse_feed()
            
        elif source.type == "telegram":
            parser = TelegramMonitor(source.id, source.name, source.telegram_channel_username)
            await parser.monitor_channel()
            
        elif source.type == "website":
            await crawl_website_source(source)

        elif source.type == "facebook":
            await crawl_facebook_source_job(source)
            
        # Update last checked timestamp
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Source).where(Source.id == source.id).values(last_checked_at=datetime.utcnow())
            )
            await session.commit()
            
    except Exception as e:
        logger.error(f"Error crawling source {source.name}: {e}", exc_info=True)


async def crawl_facebook_source_job(source: Source):
    """
    Crawls a Facebook page source, saves new event posts as RawItems.
    """
    from app.services.crawler.facebook_parser import crawl_facebook_source
    posts = await crawl_facebook_source(source)
    if not posts:
        logger.info(f"Facebook source '{source.name}': no posts returned.")
        return

    KYIV_KEYWORDS = ["київ", "киев", "kyiv", "kiev", "поділ", "хрещатик", "оболонь", "столиц"]

    async with AsyncSessionLocal() as session:
        saved = 0
        for post in posts:
            url = post.get("url", "")
            raw_text = post.get("raw_text", "")
            title = post.get("title", "")[:200]

            if not url or not raw_text:
                continue

            # Dedup check
            link_hash = compute_raw_item_hash("", url)
            q_exists = await session.execute(
                select(RawItem).where(or_(RawItem.hash == link_hash, RawItem.url == url))
            )
            if q_exists.scalar_one_or_none():
                continue

            raw_item = RawItem(
                source_id=source.id,
                external_id=None,
                url=url,
                title=title,
                raw_text=raw_text,
                image_url=post.get("image_url"),
                published_at=post.get("published_at") or datetime.utcnow(),
                fetched_at=datetime.utcnow(),
                hash=link_hash,
                processing_status="new",
            )
            session.add(raw_item)
            saved += 1

        await session.commit()
        logger.info(f"Facebook '{source.name}': saved {saved} new raw items")

        # Trigger AI processing for new items
        q_new = await session.execute(
            select(RawItem.id).where(
                and_(RawItem.source_id == source.id, RawItem.processing_status == "new")
            )
        )
        from app.tasks.worker import process_raw_item_task
        for item_id in q_new.scalars().all():
            process_raw_item_task.delay(item_id)


async def crawl_website_source(source: Source):
    """
    Fetches the website listing page and scans event details.
    """
    from app.services.crawler.generic import GenericHtmlParser
    base_parser = GenericHtmlParser(source.id, source.name, source.url)
    
    html = await base_parser.fetch_html(source.url)
    if not html:
        return
        
    try:
        event_links = set()
        parsed_base = urlparse(source.url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # 1. XML sitemap parsing support
        if source.url.endswith(".xml") or "sitemap" in source.url.lower() or html.strip().startswith("<?xml") or "<urlset" in html:
            import re
            locs = re.findall(r'<loc>([^<]+)</loc>', html)
            for loc in locs:
                parsed_loc = urlparse(loc)
                # Ensure link matches base host or subdomain
                if parsed_loc.netloc == parsed_base.netloc or parsed_loc.netloc.endswith(parsed_base.netloc.replace("www.", "")):
                    event_links.add(loc)
                    
        # 2. Gastroli.ua dynamic homepage JSON parsing support
        elif "gastroli.ua" in source.url.lower():
            import re
            soup = BeautifulSoup(html, "html.parser")
            for s in soup.find_all("script"):
                text = s.string or ""
                if "slug" in text:
                    slugs = re.findall(r'"slug"\s*:\s*"([^"]+)"', text)
                    for slug in slugs:
                        event_links.add(urljoin(source.url, f"/{slug}"))
            # Fallback to standard a tags just in case
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(source.url, href)
                parsed_full = urlparse(full_url)
                if parsed_full.netloc == parsed_base.netloc:
                    event_links.add(full_url)
                    
        # 3. Standard HTML parsing
        else:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(source.url, href)
                parsed_full = urlparse(full_url)
                if parsed_full.netloc != parsed_base.netloc:
                    continue
                event_links.add(full_url)
                
        # 4. Filter extracted URLs using advanced heuristics
        filtered_links = set()
        for link in event_links:
            parsed_link = urlparse(link)
            path = parsed_link.path
            path_lower = path.lower()
            
            # Exclude roots
            if path in ["", "/"]:
                continue
                
            # Exclude common utility pages
            if any(x in path_lower for x in [
                "login", "register", "cart", "search", "category", "categories", "checkout", "account",
                "contacts", "about", "faq", "privacy", "policy", "terms", "feedback", "support",
                "places", "venues", "halls", "order", "rules", "partnership", "catalog"
            ]):
                continue
                
            # Exclude calendar/month pages (common in Karabas)
            if any(path_lower.startswith(f"/{m}") for m in [
                "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"
            ]):
                continue
                
            # Exclude common static file extensions
            if any(path_lower.endswith(ext) for ext in [
                ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".pdf"
            ]):
                continue
                
            # Exclude generic main listing folders/pages
            if path_lower.rstrip("/") in [
                "/concerts", "/theatres", "/festivals", "/clubs", "/stand-up", "/child", "/inshe", "/planetariy",
                "/theater", "/concert", "/show", "/events", "/event", "/places", "/blog", "/activity", "/ua/events", "/en/events"
            ]:
                continue
                
            # Heuristic checks:
            # - slash_count: number of folders in path
            slash_count = path.strip("/").count("/")
            
            # - is_event_pattern: matches explicit event structures
            is_event_pattern = any(x in path_lower for x in [
                "/event/", "/events/", "/event-", "/show/", "/afisha/", "/concert/", "/ticket/", "/kiev/", "/kyiv/", "/detail/", "/p/", "/deals/item/"
            ])
            
            # - is_root_slug: root-level slug (like /anna-trincher-65/) on known sites
            is_root_slug = (slash_count == 0 and len(path.strip("/")) > 4)
            
            if is_event_pattern or is_root_slug:
                filtered_links.add(link)
                
        # Limit scan to 10 links per crawler cycle
        links_to_crawl = list(filtered_links)[:10]
        logger.info(f"Source {source.name}: Found {len(filtered_links)} event links. Scanning {len(links_to_crawl)} links.")
        
        # Kyiv-related keywords for pre-filter (Level 1 — URL hint)
        KYIV_URL_HINTS = ["kyiv", "kiev", "кiev", "kyiv", "/uk/"]
        # Kyiv-related keywords for content pre-filter (Level 2 — raw text)
        KYIV_TEXT_KEYWORDS = [
            "київ", "киев", "kyiv", "kiev", "podil", "поділ", "хрещатик",
            "оболонь", "печерськ", "шевченківськ", "деміївськ", "позняки",
            "осокорки", "троєщина", "столиц", "kyiv"
        ]
        
        async with AsyncSessionLocal() as session:
            for link in links_to_crawl:
                # --- Level 1: URL-based Kyiv hint check (for sitemaps with all-Ukraine events) ---
                link_lower = link.lower()
                # If source URL is a generic Ukrainian sitemap (not kyiv-subdomain/path),
                # skip links that have obvious non-Kyiv city names in the URL
                NON_KYIV_CITIES_IN_URL = [
                    "/lviv", "/odessa", "/odesa", "/kharkiv", "/dnipro",
                    "/zaporizhzhia", "/zaporizhia", "/vinnytsia", "/mykolaiv",
                    "/kherson", "/poltava", "/sumy", "/cherkasy", "/zhytomyr",
                    "/rivne", "/lutsk", "/ivano", "/ternopil", "/khmelnytskyi",
                    "/chernivtsi", "/uzhhorod", "/kropyvnytskyi",
                ]
                if any(city in link_lower for city in NON_KYIV_CITIES_IN_URL):
                    logger.debug(f"Skipping non-Kyiv URL: {link}")
                    continue
                
                # Check link url hash (duplicate prevention)
                link_hash = compute_raw_item_hash("", link)
                q_exists = await session.execute(
                    select(RawItem).where(
                        or_(RawItem.hash == link_hash, RawItem.url == link)
                    )
                )
                if q_exists.scalar_one_or_none():
                    continue
                    
                # Crawl detail page using site-specific or generic parser
                parser = get_parser_for_url(link, source.id, source.name)
                parsed_data = await parser.parse(link)
                if not parsed_data:
                    continue
                
                # --- Level 2: Content-based Kyiv keyword check ---
                raw_text_lower = (parsed_data.get("raw_text") or "").lower()
                title_lower = (parsed_data.get("title") or "").lower()
                combined_lower = raw_text_lower + " " + title_lower
                
                # Only skip if the source is known to have all-Ukraine events
                # (Kyiv-subdomain sites like kyiv.karabas.com are already filtered)
                source_url_lower = (source.url or "").lower()
                is_kyiv_specific_source = any(x in source_url_lower for x in [
                    "kyiv.", "/kyiv", "/kiev", "kyivmaps"
                ])
                
                if not is_kyiv_specific_source:
                    # Require at least one Kyiv keyword in content
                    has_kyiv = any(kw in combined_lower for kw in KYIV_TEXT_KEYWORDS)
                    if not has_kyiv:
                        logger.info(f"Skipping non-Kyiv content from {link} (no Kyiv keywords found).")
                        continue
                    
                # Save RawItem
                raw_item = RawItem(
                    source_id=source.id,
                    external_id=None,
                    url=link,
                    title=parsed_data["title"],
                    raw_text=parsed_data["raw_text"],
                    image_url=parsed_data.get("image_url"),
                    published_at=datetime.utcnow(),
                    fetched_at=datetime.utcnow(),
                    hash=link_hash,
                    processing_status="new"
                )
                session.add(raw_item)
                logger.info(f"Saved RawItem: '{parsed_data['title'][:50]}' from {link}")
                
            await session.commit()
            
            # Trigger celery AI task for new items
            q_new = await session.execute(
                select(RawItem.id).where(
                    and_(RawItem.source_id == source.id, RawItem.processing_status == "new")
                )
            )
            new_ids = q_new.scalars().all()
            from app.tasks.worker import process_raw_item_task
            for item_id in new_ids:
                process_raw_item_task.delay(item_id)
                
    except Exception as e:
        logger.error(f"Error parsing website listing: {e}", exc_info=True)


async def process_raw_item_job(raw_item_id: int):
    """
    AI Processing Pipeline:
    Extracts events, formats text, scores quality, saves Event record, and checks duplicates.
    """
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(RawItem).where(RawItem.id == raw_item_id))
        raw_item = q.scalar_one_or_none()
        if not raw_item or raw_item.processing_status != "new":
            return
            
        source_q = await session.execute(select(Source).where(Source.id == raw_item.source_id))
        source = source_q.scalar_one_or_none()
        source_name = source.name if source else "Unknown"

    try:
        # 1. Run AI Fact Extraction
        extracted = await ai_processor.extract_event(raw_item.raw_text, raw_item.url)
        
        async with AsyncSessionLocal() as session:
            # Re-fetch raw item in new session transaction
            raw_item = await session.merge(raw_item)
            
            if not extracted.get("is_event"):
                raw_item.processing_status = "ignored"
                await session.commit()
                logger.info(f"RawItem {raw_item_id} ignored (not an event).")
                return
                
            # 2. Run AI Scoring & Text Formatting
            quality_score = await ai_processor.score_event(extracted)
            formatted_card = await ai_processor.rewrite_event_card(extracted)
            
            # 3. Create Event record
            # Handle start/end datetime parsing from string returned by LLM
            start_dt = None
            if extracted.get("start_datetime"):
                try:
                    start_dt = datetime.fromisoformat(extracted["start_datetime"].replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
            
            end_dt = None
            if extracted.get("end_datetime"):
                try:
                    end_dt = datetime.fromisoformat(extracted["end_datetime"].replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
                    
            # Set default status depending on parameters
            # Auto review if score is high, has title, has date, and is in Kyiv
            city = extracted.get("city") or "Київ"
            status = "needs_review"
            
            # --- Level 3: AI-level Kyiv city check ---
            KYIV_SYNONYMS = ["київ", "kyiv", "киев", "kiev"]
            city_is_kyiv = any(k in city.lower() for k in KYIV_SYNONYMS)
            
            if not city_is_kyiv:
                # Also check full description for Kyiv mention as a fallback
                full_desc_lower = (extracted.get("full_description") or "").lower()
                city_is_kyiv = any(k in full_desc_lower for k in KYIV_SYNONYMS)
            
            if not start_dt or start_dt < datetime.utcnow():
                status = "draft" # no date or already passed goes to drafts
            elif quality_score < 50:
                status = "draft" # low quality goes to draft
            elif not city_is_kyiv:
                status = "draft" # Not in Kyiv — mark as draft for manual review
                logger.info(f"RawItem {raw_item_id}: city='{city}' not Kyiv, marking as draft.")
                
            event = Event(
                title=extracted.get("title") or raw_item.title or "Подія",
                short_description=formatted_card,
                full_description=extracted.get("full_description") or raw_item.raw_text,
                category=extracted.get("category"),
                subcategory=extracted.get("subcategory"),
                city=city,
                district=extracted.get("district"),
                venue_name=extracted.get("venue_name"),
                address=extracted.get("address"),
                start_datetime=start_dt,
                end_datetime=end_dt,
                date_text_original=extracted.get("date_text_original"),
                price_min=Decimal(str(extracted["price_min"])) if extracted.get("price_min") is not None else None,
                price_max=Decimal(str(extracted["price_max"])) if extracted.get("price_max") is not None else None,
                price_text_original=extracted.get("price_text_original"),
                is_free=extracted.get("is_free", False),
                ticket_url=extracted.get("ticket_url") or raw_item.url,
                source_url=raw_item.url,
                source_name=source_name,
                image_url=raw_item.image_url,
                status=status,
                quality_score=quality_score
            )
            session.add(event)
            await session.flush() # Yields event.id
            
            # Map EventSource relation
            event_source = EventSource(
                event_id=event.id,
                source_id=raw_item.source_id,
                raw_item_id=raw_item.id,
                url=raw_item.url,
                confidence=extracted.get("confidence", 1.0)
            )
            session.add(event_source)
            
            # 4. Trigger Deduplication Grouping
            await process_event_deduplication(event, session)
            
            # Mark raw item as processed
            raw_item.processing_status = "processed"
            await session.commit()
            logger.info(f"RawItem {raw_item_id} processed. Event {event.id} created with status '{status}' (score={quality_score}).")
            
            # 5. Instant Auto-Publishing Hook — strict quality gate
            if settings.AUTO_PUBLISH and status == "needs_review":
                from app.services.publisher import publish_single_event
                from app.models.models import Post

                # --- Quality gate: score, date, venue ---
                min_score = getattr(settings, 'AUTO_PUBLISH_MIN_SCORE', 65)
                if quality_score < min_score:
                    logger.info(f"Event {event.id} score={quality_score} < {min_score}, skipping auto-publish.")
                elif not event.start_datetime:
                    logger.info(f"Event {event.id} has no date, skipping auto-publish.")
                elif not event.venue_name:
                    logger.info(f"Event {event.id} has no venue, skipping auto-publish.")
                else:
                    # --- Daily post cap ---
                    max_per_day = getattr(settings, 'MAX_POSTS_PER_DAY', 8)
                    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                    q_count = await session.execute(
                        select(Post).where(
                            and_(
                                Post.status == "published",
                                Post.post_type == "single_event",
                                Post.published_at >= today_start
                            )
                        )
                    )
                    posts_today = len(q_count.scalars().all())

                    if posts_today >= max_per_day:
                        logger.info(f"Daily cap reached ({posts_today}/{max_per_day}). Event {event.id} stays in needs_review.")
                    else:
                        event = await session.merge(event)
                        success, err = await publish_single_event(event, session)
                        if success:
                            logger.info(f"Event {event.id} auto-published! ({posts_today+1}/{max_per_day} today)")
                        else:
                            logger.error(f"Auto-publish failed for Event {event.id}: {err}")
            
    except Exception as e:
        logger.error(f"Error processing RawItem {raw_item_id}: {e}", exc_info=True)
        async with AsyncSessionLocal() as session:
            raw_item = await session.merge(raw_item)
            raw_item.processing_status = "error"
            raw_item.error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            await session.commit()
