from re import findall, IGNORECASE
from logging import getLogger
from typing import Union, List, Tuple

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

# Импортируем восстановленную функцию из db_track_codes
from database.db_track_codes import add_multiple_track_codes
from keyboards import main_keyboard, cancel_keyboard, add_track_codes_follow_up_keyboard
from utils.message_common import extract_text_from_message

track_code_router = Router()
logger = getLogger(__name__)

# Этот шаблон используется и здесь, и в поиске
TRACK_CODE_PATTERN = r'[A-Z0-9]{8,}'


class TrackCodeStates(StatesGroup):
    add_multiple_codes = State()
    check_single_code = State()


# --- ОТМЕНА ---
@track_code_router.message(TrackCodeStates.add_multiple_codes, F.text.lower() == "отмена")
async def cancel_addition(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добавление трек-кодов отменено.", reply_markup=main_keyboard)


# --- ЗАПУСК ---
@track_code_router.message(F.text == "Добавить трек-кода")
@track_code_router.callback_query(F.data == "add_more_track_codes")
async def start_add_codes(event: Union[Message, CallbackQuery], state: FSMContext):
    if isinstance(event, CallbackQuery):
        message = event.message
        await event.answer()
        try:
            await message.delete()
        except:
            pass
    else:
        message = event

    await message.answer(
        "Отправьте <b>трек-код или список</b> (текстом/файлом).\n"
        "Разделители: пробел, запятая, новая строка.\n\n"
        "Пример:\n<code>78948163753575, YT7577043820770</code>",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.add_multiple_codes)


# --- ОБРАБОТКА ---
@track_code_router.message(TrackCodeStates.add_multiple_codes)
async def process_multiple_track_codes(message: Message, state: FSMContext, bot: Bot):
    # Обновление: extract_text_from_message теперь принимает bot
    raw_text = await extract_text_from_message(message, bot)

    if not raw_text:
        # Утилита сама отправит сообщение, если проблема с файлом.
        # Если это пустой текст, тут нужно решить:
        # Если файл был нечитаем, сообщение отправлено.
        # Если просто пустой текст, можно дать пользователю шанс.
        if not (message.text or message.document):
            await message.answer("Не удалось получить данные для обработки.", reply_markup=cancel_keyboard)
        return

    # Используем TRACK_CODE_PATTERN для поиска
    found_codes = findall(TRACK_CODE_PATTERN, raw_text.upper(), flags=IGNORECASE)
    unique_codes = list(set(found_codes))

    if not unique_codes:
        await message.answer(
            "❌ В тексте не найдено трек-кодов. Проверьте формат.",
            reply_markup=cancel_keyboard
        )
        return

    # Вызов восстановленной функции
    added_count, added_list = await add_multiple_track_codes(unique_codes, message.from_user.id)

    response: List[str] = [f"🔎 Обработано кодов: <b>{len(unique_codes)}</b>"]

    if added_count > 0:
        # Показываем превью добавленных
        codes_preview = "\n".join([f"• <code>{code}</code>" for code in added_list[:5]])

        preview_text = f"✅ Добавлено: <b>{added_count}</b>"
        if len(added_list) > 0:
            preview_text += f"\nПервые 5:\n{codes_preview}"

        response.append(preview_text)

    skipped = len(unique_codes) - added_count
    if skipped > 0:
        response.append(f"\n⏭️ Пропущено (уже есть): <b>{skipped}</b>")

    await message.answer("\n".join(response), reply_markup=main_keyboard)
    await state.clear()

    await message.answer(
        "Желаете добавить еще?",
        reply_markup=add_track_codes_follow_up_keyboard
    )
