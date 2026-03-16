from re import findall, IGNORECASE
from logging import getLogger
from typing import Union

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database.db_track_codes import get_user_track_codes, get_track_code
from keyboards.user_keyboards import main_keyboard, cancel_keyboard, add_track_codes_follow_up_keyboard
from utils.message_common import send_chunked_response, extract_text_from_message

from track_numbers import TRACK_CODE_PATTERN, TrackCodeStates

track_code_search_router = Router()
logger = getLogger(__name__)

STATUS_MESSAGES = {
    "in_stock": "✅ На складе",
    "out_of_stock": "⏳ Не на складе",
    "shipped": "🚚 Отправлен",
    "arrived": "📍 Прибыл в пункт выдачи! (@fir2201)"
}


# --- ТОЧКА ВХОДА ---
@track_code_search_router.message(F.text.lower() == "проверка трек-кодов")
@track_code_search_router.callback_query(F.data == "start_check_codes")
async def start_check_codes(event: Union[Message, CallbackQuery], state: FSMContext):
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
        "🔎 <b>Поиск трек-кодов</b>\n\n"
        "Отправьте <b>трек-код</b>, <b>список</b> или <b>файл</b>.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.check_single_code)


# --- ПОИСК ---
@track_code_search_router.message(TrackCodeStates.check_single_code)
async def process_track_code_search(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() == "отмена":
        await message.answer("Поиск завершён.", reply_markup=main_keyboard)
        await state.clear()
        return

    raw_text = await extract_text_from_message(message, bot)

    if not raw_text:
        if not message.document:
            await message.answer("Пожалуйста, отправьте текст или .txt файл.", reply_markup=cancel_keyboard)
        return

    track_codes = list(set(findall(TRACK_CODE_PATTERN, raw_text.upper(), flags=IGNORECASE)))

    if not track_codes:
        await message.answer("❌ Не найдено корректных трек-кодов.", reply_markup=cancel_keyboard)
        return

    user_id = message.from_user.id

    # Один код - подробно
    if len(track_codes) == 1:
        code = track_codes[0]
        info = await get_track_code(code)

        if info:
            status_text = STATUS_MESSAGES.get(info['status'], info['status'])
            owner = info.get('tg_id')

            if owner == user_id:
                ownership = "✅ <b>Это ваш код</b>"
            elif owner:
                ownership = "👤 Привязан к другому пользователю"
            else:
                ownership = "⚪️ <b>Никем не отслеживается</b>"

            response = (
                f"🔎 <b>Результат поиска</b>\n"
                f"📦 Код: <code>{code}</code>\n"
                f"ℹ️ Статус: <b>{status_text}</b>\n"
                f"🔐 {ownership}"
            )
        else:
            response = (
                f"❌ Трек-код <code>{code}</code> не найден в базе.\n"
                f"Хотите добавить его в свой список?"
            )

        await message.answer(response, reply_markup=cancel_keyboard)

    # Много кодов - списком
    else:
        result_lines = [f"📦 <b>Проверка {len(track_codes)} кодов:</b>\n"]

        for code in track_codes:
            info = await get_track_code(code)
            if info:
                status_text = STATUS_MESSAGES.get(info['status'], "Неизв.")
                is_mine = " (Ваш)" if info.get('tg_id') == user_id else ""
                result_lines.append(f"• <code>{code}</code>: {status_text}{is_mine}")
            else:
                result_lines.append(f"• <code>{code}</code>: ❌ Нет в базе")

        await send_chunked_response(message, "\n".join(result_lines))
        await message.answer("Готово! Отправьте еще или нажмите Отмена.", reply_markup=cancel_keyboard)


# --- МОИ КОДЫ ---
@track_code_search_router.callback_query(F.data == "my_track_codes")
async def view_my_track_codes(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при удалении сообщения: {e}")
    await callback.answer()

    my_codes = await get_user_track_codes(callback.from_user.id)

    if not my_codes:
        await callback.message.answer(
            "📭 Ваш список отслеживания пуст.",
            reply_markup=add_track_codes_follow_up_keyboard
        )
        return

    response_lines = [f"📋 <b>Ваши трек-коды ({len(my_codes)} шт.):</b>\n"]

    for code, status in my_codes:
        status_text = STATUS_MESSAGES.get(status, status)
        response_lines.append(f"• <code>{code}</code> — {status_text}")

    await send_chunked_response(callback, "\n".join(response_lines))

    await callback.message.answer(
        "Меню управления:",
        reply_markup=add_track_codes_follow_up_keyboard
    )
