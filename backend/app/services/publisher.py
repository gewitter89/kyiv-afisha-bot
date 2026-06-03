import httpx
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunsplit
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.models import Event, Post

logger = logging.getLogger("publisher")

# ─── Unsplash fallback images by category ─────────────────────────────────────
FALLBACK_IMAGES = {
    "concert":    "https://images.unsplash.com/photo-1540039155733-5bb30b53aa14?w=800&q=80",
    "theater":    "https://images.unsplash.com/photo-1503095396549-807759245b35?w=800&q=80",
    "standup":    "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?w=800&q=80",
    "party":      "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=800&q=80",
    "exhibition": "https://images.unsplash.com/photo-1531058020387-3be344556be6?w=800&q=80",
    "kids":       "https://images.unsplash.com/photo-1530099486328-e021101a494a?w=800&q=80",
    "food":       "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80",
    "free":       "https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800&q=80",
    "sport":      "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800&q=80",
    "workshop":   "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800&q=80",
    "cinema":     "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80",
    "deal":       "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=800&q=80",
    "restaurant": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80",
    "other":      "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800&q=80",
}

# ─── Category emoji map ────────────────────────────────────────────────────────
CAT_EMOJI = {
    "concert":    "🎸",
    "theater":    "🎭",
    "standup":    "🎙️",
    "party":      "🔥",
    "exhibition": "🎨",
    "kids":       "👶",
    "food":       "🍕",
    "bar":        "🍸",
    "restaurant": "🍽️",
    "free":       "🆓",
    "sport":      "⚽",
    "workshop":   "🛠️",
    "cinema":     "🎬",
    "lecture":    "📚",
    "date":       "💑",
    "unusual":    "🤩",
    "family":     "👨‍👩‍👧",
    "tourist":    "🏛️",
    "deal":       "💸",
    "other":      "⚡️",
}

# ─── Hashtag rubric map ───────────────────────────────────────────────────────
CAT_HASHTAG = {
    "concert":    "#концерти",
    "theater":    "#театр",
    "standup":    "#стендап",
    "party":      "#вечірки",
    "exhibition": "#виставки",
    "kids":       "#діти",
    "food":       "#їжа",
    "bar":        "#бари",
    "restaurant": "#ресторани",
    "free":       "#безкоштовно",
    "sport":      "#спорт",
    "workshop":   "#майстерклас",
    "cinema":     "#кіно",
    "lecture":    "#лекції",
    "deal":       "#знижки",
    "other":      "#афіша",
}

# ─── Affiliate UTM sources that earn commissions ──────────────────────────────
AFFILIATE_DOMAINS = {
    "karabas.com":       "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=tickets",
    "concert.ua":        "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=tickets",
    "pokupon.ua":        "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=deals",
    "multiplex.ua":      "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=cinema",
    "planeta-kino.com":  "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=cinema",
    "ticketsbox.com":    "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=tickets",
    "parter.ua":         "utm_source=kyivcityguide&utm_medium=telegram&utm_campaign=tickets",
}

# Ukrainian weekday names
UA_WEEKDAYS = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Нд"}
UA_MONTHS = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
}

def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len chars, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."


def _add_affiliate_utm(url: str) -> str:
    """Appends affiliate UTM parameters to known partner URLs."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        for affiliate_domain, utm in AFFILIATE_DOMAINS.items():
            if affiliate_domain in domain:
                separator = "&" if parsed.query else "?"
                return url + separator + utm
    except Exception:
        pass
    return url


def _get_hashtags(category: str, is_free: bool = False) -> str:
    """Returns hashtag string for the post."""
    tags = []
    cat_tag = CAT_HASHTAG.get((category or "other").lower(), "#афіша")
    tags.append(cat_tag)
    tags.append("#Київ")
    if is_free:
        tags.append("#безкоштовно")
    return " ".join(tags)


def sanitize_surrogates(text: str) -> str:
    if not isinstance(text, str):
        return text
    return "".join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))

async def send_telegram_message(
    text: str,
    photo_url: str = None,
    reply_markup: dict = None
) -> tuple[bool, Optional[int], Optional[str]]:
    """
    Sends a message to the configured Telegram Channel.
    Tries sendPhoto first if photo_url provided, falls back to sendMessage with link preview.
    Returns: (success_bool, message_id, error_message)
    """
    text = sanitize_surrogates(text)
    if reply_markup:
        def sanitize_dict_list(obj):
            if isinstance(obj, dict):
                return {k: sanitize_dict_list(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_dict_list(item) for item in obj]
            elif isinstance(obj, str):
                return sanitize_surrogates(obj)
            return obj
        reply_markup = sanitize_dict_list(reply_markup)

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
        return False, None, "Bot token or channel ID not configured."


    bot_token = settings.TELEGRAM_BOT_TOKEN
    channel_id = settings.TELEGRAM_CHANNEL_ID

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            if photo_url:
                # ── Try sendPhoto (caption max 1024 chars) ──────────────────
                caption = _truncate(text, 1024)
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                payload = {
                    "chat_id": channel_id,
                    "photo": photo_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "has_spoiler": False,
                }
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                response = await client.post(url, json=payload)
                res_json = response.json()

                if response.status_code == 200 and res_json.get("ok"):
                    message_id = res_json["result"]["message_id"]
                    logger.info(f"Sent photo post to Telegram, message_id={message_id}")
                    return True, message_id, None
                else:
                    # Photo failed — fall back to text only
                    err = res_json.get("description", "Unknown error")
                    logger.warning(f"sendPhoto failed ({err}), falling back to sendMessage.")
                    photo_url = None  # Will drop through to text send below

            # ── sendMessage (text max 4096 chars) ──────────────────────────
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": _truncate(text, 4096),
                "parse_mode": "HTML",
                "disable_web_page_preview": False,  # Shows link thumbnail if present
                "disable_notification": False,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            response = await client.post(url, json=payload)
            res_json = response.json()

            if response.status_code == 200 and res_json.get("ok"):
                message_id = res_json["result"]["message_id"]
                logger.info(f"Sent text post to Telegram, message_id={message_id}")
                return True, message_id, None
            else:
                err_msg = res_json.get("description", response.text)
                logger.error(f"Telegram API error: {err_msg}")
                return False, None, err_msg

        except Exception as e:
            logger.error(f"Exception while sending to Telegram: {e}", exc_info=True)
            return False, None, str(e)


def _format_datetime(dt: datetime) -> str:
    """Returns a beautiful Ukrainian formatted date like: 07 червня (Сб) о 20:00"""
    if not dt:
        return "Дата уточнюється"
    wd = UA_WEEKDAYS.get(dt.weekday(), "")
    month = UA_MONTHS.get(dt.month, "")
    time_str = dt.strftime("%H:%M")
    return f"{dt.day:02d} {month} ({wd}) о {time_str}"


def _get_fallback_image(category: str) -> Optional[str]:
    """Returns a high-quality fallback image URL for the given event category."""
    return FALLBACK_IMAGES.get(category or "other", FALLBACK_IMAGES["other"])


async def format_single_event_card(event: Event) -> str:
    """
    Formats a premium HTML event card for Telegram channel posts.
    Uses HTML parse_mode for rich formatting.
    """
    cat = (event.category or "other").lower()
    emoji = CAT_EMOJI.get(cat, "⚡️")

    # Title — bold uppercase
    title = (event.title or "Подія").upper()

    # Description — from short_description (AI-generated) or fallback
    desc = event.short_description or "Неймовірна подія у столиці, яку точно варто відвідати! 🔥"
    desc = desc.strip()

    # Date
    if event.start_datetime:
        date_str = _format_datetime(event.start_datetime)
    else:
        date_str = event.date_text_original or "Уточнюється"

    # Venue
    venue_str = event.venue_name or "Київ"
    if event.district and event.district.lower() not in venue_str.lower():
        venue_str = f"{venue_str} • {event.district}"

    # Price
    if event.is_free:
        price_str = "🆓 Вхід ВІЛЬНИЙ"
    elif event.price_min is not None:
        if event.price_max and event.price_max > event.price_min:
            price_str = f"від {int(event.price_min)} до {int(event.price_max)} грн"
        else:
            price_str = f"від {int(event.price_min)} грн"
    else:
        price_str = event.price_text_original or "Уточнюється"

    # Hashtags
    hashtags = _get_hashtags(cat, event.is_free)

    # Source tag
    source_tag = f"<i>\ud83d\udccc {event.source_name}</i>" if event.source_name else ""

    # Special deal/cinema format
    if cat in ["deal"]:
        card = (
            f"💸 <b>{title}</b>\n"
            f"\n"
            f"{desc}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Де:</b> {venue_str}\n"
            f"💵 <b>Ціна:</b> {price_str}\n"
            f"⏰ <b>Діє:</b> {date_str}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"{hashtags}"
            + (f"\n{source_tag}" if source_tag else "")
        )
    else:
        card = (
            f"{emoji} <b>{title}</b>\n"
            f"\n"
            f"{desc}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Де:</b> {venue_str}\n"
            f"📅 <b>Коли:</b> {date_str}\n"
            f"💸 <b>Ціна:</b> {price_str}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"{hashtags}"
            + (f"\n{source_tag}" if source_tag else "")
        )

    return card


def _build_event_buttons(event: Event) -> Optional[dict]:
    """Builds inline keyboard buttons with affiliate UTM links."""
    buttons_row = []

    link = event.ticket_url or event.source_url
    if link:
        # Add affiliate UTM
        link = _add_affiliate_utm(link)

        if event.is_free:
            btn_text = "🆓 Деталі події"
        elif event.category == "deal" or "pokupon.ua" in (event.source_url or "").lower():
            btn_text = "💸 Отримати знижку"
        elif event.category == "cinema":
            btn_text = "🎬 Купити квиток"
        elif event.category == "sport":
            btn_text = "⚽ Купити квиток"
        elif event.category in ["concert", "theater", "standup"]:
            btn_text = "🎟️ Купити квитки"
        else:
            btn_text = "🎟️ Деталі та квитки"
        buttons_row.append({"text": btn_text, "url": link})

    if not buttons_row:
        return None

    return {"inline_keyboard": [buttons_row]}



async def publish_single_event(event: Event, db: AsyncSession) -> tuple[bool, Optional[str]]:
    """
    Publishes a single event card to the Telegram Channel with photo if available.
    """
    card_text = await format_single_event_card(event)
    reply_markup = _build_event_buttons(event)

    # Pick image: use event image or smart fallback by category
    photo_url = event.image_url
    if not photo_url:
        photo_url = _get_fallback_image(event.category)
        logger.info(f"No image for Event {event.id}, using fallback image for category '{event.category}'.")

    success, message_id, error_msg = await send_telegram_message(card_text, photo_url, reply_markup)

    # Save post record
    post = Post(
        event_id=event.id,
        post_type="single_event",
        telegram_channel_id=settings.TELEGRAM_CHANNEL_ID,
        telegram_message_id=message_id,
        text=card_text,
        status="published" if success else "failed",
        scheduled_at=datetime.utcnow(),
        published_at=datetime.utcnow() if success else None,
        error_message=error_msg
    )
    db.add(post)

    if success:
        event.status = "published"
        event.published_to_telegram_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Event {event.id} published to Telegram channel successfully.")
        return True, None
    else:
        await db.commit()
        logger.error(f"Event {event.id} failed to publish: {error_msg}")
        return False, error_msg


async def generate_and_publish_daily_digest(db: AsyncSession, for_tomorrow: bool = False) -> tuple[Optional[Post], Optional[str]]:
    """
    Gathers approved/published events for today or tomorrow and posts a premium digest.
    """
    now = datetime.utcnow()
    target_date = now.date() + timedelta(days=1) if for_tomorrow else now.date()
    target_start = datetime.combine(target_date, time.min)
    target_end = datetime.combine(target_date, time.max)

    q = await db.execute(
        select(Event).where(
            and_(
                Event.status.in_(["approved", "published"]),
                Event.start_datetime >= target_start,
                Event.start_datetime <= target_end
            )
        ).order_by(Event.start_datetime.asc())
    )
    events = q.scalars().all()

    target_day_name = "tomorrow" if for_tomorrow else "today"
    if not events:
        return None, f"No events scheduled for {target_day_name} to generate digest."

    # Day of week in Ukrainian
    wd_name = UA_WEEKDAYS.get(target_date.weekday(), "")
    day_label = f"{target_date.day:02d} {UA_MONTHS.get(target_date.month, '')} ({wd_name})"

    # Fetch weather for today
    weather_line = ""
    if not for_tomorrow:
        try:
            from app.services.weather import get_kyiv_weather, format_weather_line
            weather = await get_kyiv_weather()
            if weather:
                weather_line = format_weather_line(weather) + "\n"
        except Exception as e:
            logger.warning(f"Could not get Kyiv weather: {e}")

    if for_tomorrow:
        digest_text = (
            f"🌅 <b>КИЇВ ЗАВТРА — {day_label}</b>\n"
            f"<i>{len(events)} крутих ідей куди піти завтра!</i>\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━\n"
        )
    else:
        digest_text = (
            f"🔥 <b>КИЇВ СЬОГОДНІ — {day_label}</b>\n"
            f"{weather_line}"
            f"<i>{len(events)} крутих ідей куди піти!</i>\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━\n"
        )

    for i, event in enumerate(events, 1):
        cat = (event.category or "other").lower()
        emoji = CAT_EMOJI.get(cat, "⚡️")
        price_str = "Безкоштовно 🆓" if event.is_free else (f"від {int(event.price_min)} грн" if event.price_min else "уточн.")
        time_str = event.start_datetime.strftime("%H:%M") if event.start_datetime else "—"
        venue_str = event.venue_name or "Київ"
        link = event.ticket_url or event.source_url

        digest_text += f"\n{i}. {emoji} <b>{event.title}</b>\n"
        digest_text += f"   📍 {venue_str}  ·  🕐 {time_str}  ·  💸 {price_str}\n"
        if link:
            digest_text += f"   <a href=\"{link}\">👉 Деталі</a>\n"

    digest_text += (
        f"\n━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Більше ідей та фільтри — у нашому боті!</i>"
    )

    success, message_id, error_msg = await send_telegram_message(digest_text)

    post = Post(
        event_id=None,
        post_type="daily_digest",
        telegram_channel_id=settings.TELEGRAM_CHANNEL_ID,
        telegram_message_id=message_id,
        text=digest_text,
        status="published" if success else "failed",
        scheduled_at=datetime.utcnow(),
        published_at=datetime.utcnow() if success else None,
        error_message=error_msg
    )
    db.add(post)
    await db.commit()

    if success:
        return post, None
    else:
        return None, error_msg


async def generate_and_publish_weekend_digest(db: AsyncSession) -> tuple[Optional[Post], Optional[str]]:
    """
    Gathers approved/published events for the upcoming weekend and posts a premium digest.
    """
    now = datetime.utcnow()
    days_to_sat = (5 - now.weekday()) % 7
    sat = now.date() + timedelta(days=days_to_sat)
    sun = sat + timedelta(days=1)

    weekend_start = datetime.combine(sat, time.min)
    weekend_end = datetime.combine(sun, time.max)

    q = await db.execute(
        select(Event).where(
            and_(
                Event.status.in_(["approved", "published"]),
                Event.start_datetime >= weekend_start,
                Event.start_datetime <= weekend_end
            )
        ).order_by(Event.start_datetime.asc())
    )
    events = q.scalars().all()

    if not events:
        return None, "No events scheduled for the weekend to generate digest."

    sat_label = f"{sat.day} {UA_MONTHS.get(sat.month, '')} ({UA_WEEKDAYS[5]})"
    sun_label = f"{sun.day} {UA_MONTHS.get(sun.month, '')} ({UA_WEEKDAYS[6]})"

    digest_text = (
        f"🎉 <b>ВИХІДНІ В КИЄВІ — {sat_label} та {sun_label}</b>\n"
        f"<i>Відбираємо найкраще для тебе!</i>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━\n"
    )

    for i, event in enumerate(events, 1):
        cat = (event.category or "other").lower()
        emoji = CAT_EMOJI.get(cat, "⚡️")
        price_str = "Безкоштовно 🆓" if event.is_free else (f"від {int(event.price_min)} грн" if event.price_min else "уточн.")
        day_name = UA_WEEKDAYS.get(event.start_datetime.weekday(), "") if event.start_datetime else ""
        time_str = f"{day_name} {event.start_datetime.strftime('%H:%M')}" if event.start_datetime else "—"
        venue_str = event.venue_name or "Київ"
        link = event.ticket_url or event.source_url

        digest_text += f"\n{i}. {emoji} <b>{event.title}</b>\n"
        digest_text += f"   📍 {venue_str}  ·  🕐 {time_str}  ·  💸 {price_str}\n"
        if link:
            digest_text += f"   <a href=\"{link}\">👉 Деталі</a>\n"

    digest_text += (
        f"\n━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Повний список — у боті. Гарних вихідних! 🥂</i>"
    )

    success, message_id, error_msg = await send_telegram_message(digest_text)

    post = Post(
        event_id=None,
        post_type="weekend_digest",
        telegram_channel_id=settings.TELEGRAM_CHANNEL_ID,
        telegram_message_id=message_id,
        text=digest_text,
        status="published" if success else "failed",
        scheduled_at=datetime.utcnow(),
        published_at=datetime.utcnow() if success else None,
        error_message=error_msg
    )
    db.add(post)
    await db.commit()

    if success:
        return post, None
    else:
        return None, error_msg
