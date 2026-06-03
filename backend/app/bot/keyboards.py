from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns the main menu keyboard with 2 columns of filter options.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Сьогодні"), KeyboardButton(text="🌅 Завтра")],
            [KeyboardButton(text="🎉 Вихідні"), KeyboardButton(text="🆓 Безкоштовно")],
            [KeyboardButton(text="❤️ Для побачення"), KeyboardButton(text="👶 З дітьми")],
            [KeyboardButton(text="🕺 Тусовки"), KeyboardButton(text="➕ Додати подію")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Оберіть розділ або напишіть команду"
    )
    return keyboard

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard shown during event submission flow to allow cancellation.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Скасувати")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard shown during optional fields (e.g. photo or link) to allow skipping.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➡️ Пропустити")],
            [KeyboardButton(text="❌ Скасувати")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
