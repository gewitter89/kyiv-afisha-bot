from datetime import datetime, timedelta, time
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select, and_, or_, any_
from app.core.database import AsyncSessionLocal
from app.models.models import Event
from app.bot.keyboards import get_main_menu_keyboard

router = Router()

def get_today_range():
    now = datetime.utcnow()
    # Adjust for Kyiv timezone (UTC+2 or UTC+3, let's keep it simple UTC for database, or just query UTC)
    # Kyiv is UTC+2 (winter) or UTC+3 (summer). Let's use local date.
    # To be safe, let's do a wide window or convert
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)
    return today_start, today_end

def get_tomorrow_range():
    now = datetime.utcnow()
    tomorrow = now.date() + timedelta(days=1)
    tomorrow_start = datetime.combine(tomorrow, time.min)
    tomorrow_end = datetime.combine(tomorrow, time.max)
    return tomorrow_start, tomorrow_end

def get_weekend_range():
    now = datetime.utcnow()
    # Find next Saturday (5) and Sunday (6)
    days_to_sat = (5 - now.weekday()) % 7
    if days_to_sat == 0 and now.weekday() == 5:
        # If today is Saturday, show this weekend
        sat = now.date()
    else:
        sat = now.date() + timedelta(days=days_to_sat)
    
    sun = sat + timedelta(days=1)
    weekend_start = datetime.combine(sat, time.min)
    weekend_end = datetime.combine(sun, time.max)
    return weekend_start, weekend_end

async def fetch_and_send_events(message: Message, stmt, title_prefix: str):
    """
    Utility helper to execute query, format cards, and send to the user.
    """
    async with AsyncSessionLocal() as session:
        q = await session.execute(stmt.limit(7))
        events = q.scalars().all()
        
    if not events:
        weather_line = ""
        if "сьогодні" in title_prefix.lower():
            try:
                from app.services.weather import get_kyiv_weather, format_weather_line
                weather = await get_kyiv_weather()
                if weather:
                    weather_line = format_weather_line(weather) + "\n\n"
            except Exception:
                pass
        await message.answer(
            f"{weather_line}ℹ️ {title_prefix}\n\nНа жаль, наразі немає актуальних подій у цій категорії. Спробуйте інші розділи або завітайте пізніше!",
            reply_markup=get_main_menu_keyboard()
        )
        return

    weather_line = ""
    if "сьогодні" in title_prefix.lower():
        try:
            from app.services.weather import get_kyiv_weather, format_weather_line
            weather = await get_kyiv_weather()
            if weather:
                weather_line = format_weather_line(weather) + "\n\n"
        except Exception:
            pass

    await message.answer(f"{weather_line}🔥 {title_prefix}:")
    
    for event in events:
        # Format date
        date_str = event.date_text_original or ""
        if event.start_datetime:
            date_str = event.start_datetime.strftime("%d.%m.%Y %H:%M")
            if event.end_datetime:
                date_str += f" - {event.end_datetime.strftime('%H:%M')}"
        
        # Format price
        price_str = event.price_text_original or ""
        if event.is_free:
            price_str = "Безкоштовно"
        elif event.price_min is not None:
            if event.price_max and event.price_max > event.price_min:
                price_str = f"від {int(event.price_min)} до {int(event.price_max)} грн"
            else:
                price_str = f"{int(event.price_min)} грн"
        
        # Format venue
        venue_str = event.venue_name or "Уточнюється"
        if event.district:
            venue_str = f"{venue_str} ({event.district})"
        if event.address:
            venue_str = f"{venue_str}, {event.address}"
            
        card = (
            f"🎭 **{event.title}**\n\n"
            f"📅 **Дата:** {date_str}\n"
            f"📍 **Місце:** {venue_str}\n"
            f"💸 **Ціна:** {price_str}\n\n"
            f"⭐ **Чому варто піти:**\n{event.short_description or 'Цікава подія у Києві!'}\n"
        )
        
        # Construct keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = None
        link = event.ticket_url or event.source_url
        if link:
            btn_text = "🎟️ Деталі та квитки"
            if event.category == "free":
                btn_text = "🆓 Вхід вільний / Деталі"
            elif "pokupon" in link.lower():
                btn_text = "💸 Отримати знижку"
                
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=btn_text, url=link)]
                ]
            )
            
        # Send card (if there is an image, we can try sending it as photo)
        if event.image_url:
            try:
                await message.answer_photo(
                    photo=event.image_url,
                    caption=card,
                    parse_mode="Markdown",
                    reply_markup=kb
                )
                continue
            except Exception:
                # Fallback to text message if photo URL is invalid or blocked
                pass
                
        await message.answer(card, parse_mode="Markdown", disable_web_page_preview=False, reply_markup=kb)

@router.message(CommandStart())
async def cmd_start(message: Message):
    greeting = (
        "👋 Привіт! Я твій гід подіями столиці — **«Куди піти Київ»**.\n\n"
        "Я допоможу тобі швидко знайти найцікавіші концерти, виставки, вистави, вечірки та безкоштовні заходи.\n\n"
        "Обирай категорію нижче або скористайся меню, щоб знайти подію до душі!"
    )
    await message.answer(greeting, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

# --- FILTER HANDLERS ---

@router.message(F.text == "📅 Сьогодні")
@router.message(Command("today"))
async def filter_today(message: Message):
    start, end = get_today_range()
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            Event.start_datetime >= start,
            Event.start_datetime <= end
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Події на сьогодні")

@router.message(F.text == "🌅 Завтра")
@router.message(Command("tomorrow"))
async def filter_tomorrow(message: Message):
    start, end = get_tomorrow_range()
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            Event.start_datetime >= start,
            Event.start_datetime <= end
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Події на завтра")

@router.message(F.text == "🎉 Вихідні")
@router.message(Command("weekend"))
async def filter_weekend(message: Message):
    start, end = get_weekend_range()
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            Event.start_datetime >= start,
            Event.start_datetime <= end
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Події на вихідні")

@router.message(F.text == "🆓 Безкоштовно")
@router.message(Command("free"))
async def filter_free(message: Message):
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            or_(
                Event.is_free == True,
                Event.price_min == 0,
                Event.category == "free"
            ),
            Event.start_datetime >= datetime.utcnow()
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Безкоштовні події")

@router.message(F.text == "❤️ Для побачення")
@router.message(Command("date"))
async def filter_date(message: Message):
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            Event.category == "date",
            Event.start_datetime >= datetime.utcnow()
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Ідеї для побачень")

@router.message(F.text == "👶 З дітьми")
@router.message(Command("kids"))
async def filter_kids(message: Message):
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            Event.category.in_(["kids", "family"]),
            Event.start_datetime >= datetime.utcnow()
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Куди піти з дітьми")

@router.message(F.text == "🕺 Тусовки")
@router.message(Command("party"))
async def filter_party(message: Message):
    stmt = select(Event).where(
        and_(
            Event.status.in_(["approved", "published"]),
            Event.category.in_(["party", "bar", "restaurant"]),
            Event.start_datetime >= datetime.utcnow()
        )
    ).order_by(Event.start_datetime.asc())
    await fetch_and_send_events(message, stmt, "Вечірки та тусовки")
