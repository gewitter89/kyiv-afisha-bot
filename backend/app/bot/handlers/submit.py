from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy import insert

from app.core.database import AsyncSessionLocal
from app.models.models import Submission
from app.bot.keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_skip_keyboard

router = Router()

class SubmitEventState(StatesGroup):
    title = State()
    description = State()
    date_text = State()
    venue = State()
    address = State()
    price_text = State()
    link = State()
    photo = State()

# --- GLOBAL CANCEL HANDLER ---
@router.message(StateFilter("*"), F.text == "❌ Скасувати")
async def cancel_submission(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Створення події скасовано.",
        reply_markup=get_main_menu_keyboard()
    )

# --- START FLOW ---
@router.message(F.text == "➕ Додати подію")
@router.message(Command("submit"))
async def start_submit(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SubmitEventState.title)
    await message.answer(
        "📝 Розпочнемо додавання події!\n\n"
        "Введіть **назву події** (наприклад: *Джаз-вечір на Подолі*):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

# --- TITLE ---
@router.message(SubmitEventState.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(SubmitEventState.description)
    await message.answer(
        "📝 Введіть **опис події** (розкажіть детальніше, що цікавого буде відбуватися):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

# --- DESCRIPTION ---
@router.message(SubmitEventState.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(SubmitEventState.date_text)
    await message.answer(
        "📅 Введіть **дату та час** події (наприклад: *Сьогодні о 19:00*, *Кожної суботи о 18:00* або *5 червня, 18:30*):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

# --- DATE TEXT ---
@router.message(SubmitEventState.date_text)
async def process_date(message: Message, state: FSMContext):
    await state.update_data(date_text=message.text)
    await state.set_state(SubmitEventState.venue)
    await message.answer(
        "📍 Введіть **назву локації** (наприклад: *Подол 32*, *ВДНГ, павільйон 1* або *клуб Атлас*):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

# --- VENUE ---
@router.message(SubmitEventState.venue)
async def process_venue(message: Message, state: FSMContext):
    await state.update_data(venue=message.text)
    await state.set_state(SubmitEventState.address)
    await message.answer(
        "📍 Введіть **точну адресу локації** (наприклад: *вул. Нижній Вал, 33*):\n\n"
        "Або натисніть кнопку «Пропустити», якщо адреса відома за назвою місця.",
        reply_markup=get_skip_keyboard(),
        parse_mode="Markdown"
    )

# --- ADDRESS ---
@router.message(SubmitEventState.address)
async def process_address(message: Message, state: FSMContext):
    if message.text == "➡️ Пропустити":
        await state.update_data(address=None)
    else:
        await state.update_data(address=message.text)
        
    await state.set_state(SubmitEventState.price_text)
    await message.answer(
        "💸 Введіть **ціну або вартість квитків** (наприклад: *від 400 грн*, *300 грн* або *Вхід вільний*):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

# --- PRICE TEXT ---
@router.message(SubmitEventState.price_text)
async def process_price(message: Message, state: FSMContext):
    await state.update_data(price_text=message.text)
    await state.set_state(SubmitEventState.link)
    await message.answer(
        "🔗 Введіть **посилання на квитки або детальну інформацію** (починається з http/https):\n\n"
        "Або натисніть «Пропустити», якщо посилання немає.",
        reply_markup=get_skip_keyboard(),
        parse_mode="Markdown"
    )

# --- LINK ---
@router.message(SubmitEventState.link)
async def process_link(message: Message, state: FSMContext):
    if message.text == "➡️ Пропустити":
        await state.update_data(link=None)
    else:
        # Simple verification
        if not message.text.startswith(("http://", "https://")):
            await message.answer("⚠️ Будь ласка, введіть коректне посилання (з http:// або https://) або натисніть «Пропустити»:")
            return
        await state.update_data(link=message.text)
        
    await state.set_state(SubmitEventState.photo)
    await message.answer(
        "🖼️ Надішліть **фото афіші** для цієї події:\n\n"
        "Або натисніть «Пропустити», якщо фотографії немає.",
        reply_markup=get_skip_keyboard(),
        parse_mode="Markdown"
    )

# --- PHOTO ---
@router.message(SubmitEventState.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_file_id = None
    
    if message.text == "➡️ Пропустити":
        pass
    elif message.photo:
        # Get highest resolution image
        photo_file_id = message.photo[-1].file_id
    else:
        await message.answer("⚠️ Будь ласка, надішліть зображення або натисніть кнопку «Пропустити»:")
        return

    data = await state.get_data()
    await state.clear()
    
    # Save submission in database
    async with AsyncSessionLocal() as session:
        submission = Submission(
            user_id=message.from_user.id,
            username=message.from_user.username,
            title=data["title"],
            description=data["description"],
            date_text=data["date_text"],
            venue=data["venue"],
            address=data.get("address"),
            price_text=data["price_text"],
            link=data.get("link"),
            image_file_id=photo_file_id,
            status="new"
        )
        session.add(submission)
        await session.commit()

    success_msg = (
        "🎉 **Дякуємо! Вашу подію відправлено на модерацію.**\n\n"
        "Наші редактори перевірять інформацію найближчим часом. "
        "У разі успішного проходження перевірки подія з'явиться в афіші та каналі!"
    )
    await message.answer(
        success_msg,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
