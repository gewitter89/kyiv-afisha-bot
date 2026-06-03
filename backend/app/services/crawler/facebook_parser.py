import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger("facebook_parser")

# Known Kyiv Facebook event pages (page_username -> display_name)
KYIV_FB_PAGES = [
    "PalatsUkrainy",        # Палац Україна
    "AtlasKyiv",            # Клуб Атлас
    "mistokyiv",            # Місто Київ
    "kyivtoday",            # Kyiv Today
    "ConcertUaOfficial",    # Concert.ua
    "karabastickets",       # Karabas
    "RePublicKyiv",         # RePublic
    "SentoCLUB",            # Sento Club
    "FreeDomClubKyiv",      # FreeDom Club
    "PostPlayTheater",      # Teatr Postplay
    "kyivoperaballet",      # Opera Kyiv
    "KyivMusicFilmFestival",
]

# Keywords signaling an event post
EVENT_KEYWORDS = [
    "концерт", "вистава", "шоу", "фестиваль", "виставка",
    "квитки", "вхід", "початок", "запрошуємо", "приходьте",
    "стендап", "stand-up", "вечірка", "перформанс", "прем'єра",
    "tickets", "event", "show", "concert", "festival", "party",
    "відбудеться", "запрошує", "зустрічаємося",
]

NON_KYIV_CITIES = [
    "львів", "одеса", "харків", "дніпро", "запоріжж",
    "вінниця", "полтава", "суми", "чернівці",
    "lviv", "odessa", "kharkiv", "dnipro",
]

IMAGE_SKIP = ["profile", "cover", "avatar", "logo", "icon", "1x1", "pixel"]


def _is_good_image(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    url_lower = url.lower()
    return not any(skip in url_lower for skip in IMAGE_SKIP)


class FacebookParser:
    """
    Authenticated Facebook page scraper using facebook-scraper library.
    Uses login credentials for richer access to event posts.
    """

    def __init__(self, source_id: int, source_name: str, page_username: str, posts_count: int = 15):
        self.source_id = source_id
        self.source_name = source_name
        self.page_username = page_username
        self.posts_count = posts_count

    async def get_posts(self) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            posts = await loop.run_in_executor(None, self._fetch_sync)
            return posts
        except Exception as e:
            logger.error(f"[FB] Failed to fetch @{self.page_username}: {e}")
            return []

    def _fetch_sync(self) -> List[Dict[str, Any]]:
        try:
            from facebook_scraper import get_posts as fb_get_posts, set_cookies
        except ImportError:
            logger.error("[FB] facebook-scraper not installed. Run: pip install facebook-scraper")
            return []

        from app.core.config import settings

        # Use authenticated session if credentials available
        options = {
            "posts_per_page": self.posts_count,
            "allow_extra_requests": True,
            "progress": False,
            "reactions": False,
            "comments": False,
        }

        credentials = None
        if settings.FACEBOOK_EMAIL and settings.FACEBOOK_PASSWORD:
            credentials = (settings.FACEBOOK_EMAIL, settings.FACEBOOK_PASSWORD)
            logger.info(f"[FB] Using authenticated session for @{self.page_username}")
        else:
            logger.warning(f"[FB] No FB credentials — scraping as guest (limited access)")

        results = []
        try:
            for post in fb_get_posts(
                self.page_username,
                pages=3,
                credentials=credentials,
                options=options,
            ):
                parsed = self._parse_post(post)
                if parsed:
                    results.append(parsed)
                if len(results) >= self.posts_count:
                    break
        except Exception as e:
            logger.warning(f"[FB] Scrape error @{self.page_username}: {type(e).__name__}: {e}")

        logger.info(f"[FB] @{self.page_username}: {len(results)} event posts found")
        return results

    def _parse_post(self, post: dict) -> Optional[Dict[str, Any]]:
        text = (
            post.get("post_text")
            or post.get("text")
            or post.get("shared_text")
            or ""
        ).strip()

        if not text or len(text) < 40:
            return None

        text_lower = text.lower()

        # Must contain event keywords
        if not any(kw in text_lower for kw in EVENT_KEYWORDS):
            return None

        # Skip posts mentioning non-Kyiv cities explicitly
        if any(city in text_lower for city in NON_KYIV_CITIES):
            return None

        # --- Extract image ---
        image_url = None
        for key in ["image", "images", "header_image"]:
            val = post.get(key)
            if isinstance(val, list):
                for img in val:
                    if _is_good_image(img):
                        image_url = img
                        break
            elif isinstance(val, str) and _is_good_image(val):
                image_url = val
            if image_url:
                break

        # --- Extract URL ---
        post_url = (
            post.get("post_url")
            or post.get("link")
            or f"https://www.facebook.com/{self.page_username}"
        )

        # --- Extract date ---
        published_at = None
        for key in ["time", "timestamp"]:
            ts = post.get(key)
            if ts:
                try:
                    if isinstance(ts, (int, float)):
                        published_at = datetime.utcfromtimestamp(ts)
                    elif isinstance(ts, datetime):
                        published_at = ts
                    break
                except Exception:
                    pass

        # --- Extract event-specific fields if available ---
        event_data = post.get("event") or {}
        event_start = event_data.get("start_time") or event_data.get("start_datetime")
        event_location = event_data.get("location") or event_data.get("venue", {})
        if isinstance(event_location, dict):
            event_location = event_location.get("name", "")

        # --- Build title ---
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3]
        title = lines[0][:120] if lines else text[:80]

        # Build enriched raw_text
        raw_text = f"Title: {title}\n\nContent:\n{text}"
        if event_location:
            raw_text += f"\n\nLocation: {event_location}"
        if event_start:
            raw_text += f"\nDate: {event_start}"

        return {
            "title": title,
            "raw_text": raw_text,
            "description": text[:400],
            "image_url": image_url,
            "url": post_url,
            "published_at": published_at,
            "source": f"Facebook / {self.source_name}",
        }


async def crawl_facebook_source(source) -> List[Dict[str, Any]]:
    """
    Crawl a Facebook source record.
    Uses facebook_page_username field (stored in telegram_channel_username for compatibility).
    """
    fb_username = (
        getattr(source, "facebook_page_username", None)
        or getattr(source, "telegram_channel_username", None)
    )
    if not fb_username:
        logger.warning(f"[FB] Source '{source.name}' has no facebook page username configured")
        return []

    parser = FacebookParser(
        source_id=source.id,
        source_name=source.name,
        page_username=fb_username,
        posts_count=20,
    )
    return await parser.get_posts()
