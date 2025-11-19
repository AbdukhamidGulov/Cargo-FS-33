import re
from logging import getLogger
from typing import Union

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from database.db_track_codes import add_multiple_track_codes
from keyboards import main_keyboard, cancel_keyboard, add_track_codes_follow_up_keyboard
from utils.message_common import extract_text_from_message

track_code_router = Router()
logger = getLogger(__name__)

# Минимум 8 символов, латиница и цифры
TRACK_CODE_PATTERN = r'[A-Z0-9]{8,}'


class TrackCodeStates(StatesGroup):
    add_multiple_codes = State()


# --- ОБЩАЯ ОТМЕНА ---
@track_code_router.message(TrackCodeStates.add_multiple_codes, F.text.lower() == "отмена")
async def cancel_addition(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добавление трек-кодов отменено.", reply_markup=main_keyboard)


# --- ЗАПУСК ПРОЦЕССА (Кнопка меню или Inline) ---
@track_code_router.message(F.text == "Добавить трек-кода")
@track_code_router.callback_query(F.data == "add_more_track_codes")
async def start_add_codes(event: Union[Message, CallbackQuery], state: FSMContext):
    # Определяем message в зависимости от типа события
    if isinstance(event, CallbackQuery):
        message = event.message
        await event.answer()
        try:
            await message.delete()  # Удаляем старое сообщение с inline кнопками, чтобы не захламлять чат
        except:
            pass
    else:
        message = event

    await message.answer(
        "Отправьте <b>трек-код или список</b> (текстом/файлом).\n"
        "<i>Разделители: пробел, запятая, новая строка.<i>\n\n"
        "Пример:\n<code>78948163753575, YT7577043820770</code>",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.add_multiple_codes)


# --- ОБРАБОТКА КОДОВ ---
@track_code_router.message(TrackCodeStates.add_multiple_codes)
async def process_multiple_track_codes(message: Message, state: FSMContext, bot: Bot):
    raw_text = await extract_text_from_message(message, bot)

    if not raw_text:
        return  # Ошибку уже вывела утилита extract_text_from_message

    # Ищем коды (сразу в верхнем регистре) и убираем дубликаты
    found_codes = re.findall(TRACK_CODE_PATTERN, raw_text.upper())
    unique_codes = list(set(found_codes))

    if not unique_codes:
        await message.answer(
            "❌ В тексте не найдено трек-кодов. Проверьте формат.",
            reply_markup=cancel_keyboard
        )
        return

    # Массовое добавление в БД
    added_count, added_list = await add_multiple_track_codes(unique_codes, message.from_user.id)

    # Формирование отчета
    response = [f"🔎 Обработано кодов: <b>{len(unique_codes)}</b>"]

    if added_count > 0:
        codes_preview = "\n".join([f"• <code>{code}</code>" for code in added_list])
        response.append(f"✅ Добавлено: <b>{added_count}</b>\n{codes_preview}")

    skipped = len(unique_codes) - added_count
    if skipped > 0:
        response.append(f"\n⏭️ Пропущено (уже есть): <b>{skipped}</b>")

    # 1. Итог
    await message.answer("\n".join(response), reply_markup=main_keyboard)
    await state.clear()

    # 2. Предложение продолжить
    await message.answer(
        "Желаете добавить еще?",
        reply_markup=add_track_codes_follow_up_keyboard
    )
