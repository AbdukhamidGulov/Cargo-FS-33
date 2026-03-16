from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup


def create_keyboard_button(text: str) -> KeyboardButton:
    """Создаёт кнопку для обычной клавиатуры."""
    return KeyboardButton(text=text)


def create_keyboard(
        buttons: list[list[KeyboardButton]],
        resize: bool = True,
        selective: bool = False
) -> ReplyKeyboardMarkup:
    """Создаёт обычную клавиатуру с заданными кнопками."""
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=resize,
        selective=selective
    )


def create_inline_button(text: str, callback_data: str = None, url: str = None) -> InlineKeyboardButton:
    """Создаёт инлайн-кнопку с текстом и callback_data или URL."""
    if url: return InlineKeyboardButton(text=text, url=url)
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру с заданными кнопками."""
    return InlineKeyboardMarkup(inline_keyboard=buttons)
