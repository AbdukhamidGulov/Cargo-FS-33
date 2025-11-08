import re
from logging import getLogger
from typing import List

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.track_codes import get_track_code_status, get_user_track_codes
from keyboards import main_keyboard, cancel_keyboard, add_track_codes_follow_up_keyboard
from track_numbers import TRACK_CODE_PATTERN, status_messages, TrackCodeStates

track_code_search_router = Router()
logger = getLogger(__name__)


def parse_track_codes(text: str) -> List[str]:
    """Разделяет введенный текст на список потенциальных трек-кодов."""
    # Ищем все совпадения с паттерном в тексте.
    # Это автоматически игнорирует любой "мусор" между кодами.
    return re.findall(TRACK_CODE_PATTERN, text, re.IGNORECASE)


async def send_chunked_response(message: Message, text: str):
    """
    Отправляет длинный текст, разбивая его на части по 4096 символов.
    Разбивка происходит строго по переносам строк, чтобы не ломать HTML-разметку.
    """
    LIMIT = 4096

    if len(text) <= LIMIT:
        await message.answer(text)
        return

    lines = text.splitlines()
    current_chunk = []
    current_length = 0

    for line in lines:
        # +1 учитывает невидимый символ переноса строки \n
        line_len = len(line) + 1

        # Если добавление следующей строки превысит лимит
        if current_length + line_len > LIMIT:
            # Отправляем то, что накопили
            await message.answer("\n".join(current_chunk))
            # Начинаем новый кусок с текущей строки
            current_chunk = [line]
            current_length = line_len
        else:
            # Иначе просто добавляем строку в текущий кусок
            current_chunk.append(line)
            current_length += line_len

    # Отправляем последний оставшийся кусок, если он есть
    if current_chunk:
        await message.answer("\n".join(current_chunk))


# ************************************************
# 1. ПРОВЕРКА ОДНОГО/НЕСКОЛЬКИХ ТРЕК-КОДОВ
# ************************************************

@track_code_search_router.message(F.text.lower() == "проверка трек-кодов")
async def check_track_code(message: Message, state: FSMContext) -> None:
    """Запускает процесс проверки статуса трек-кода."""
    await message.answer(
        "Отправьте ваш <b>трек-код</b> или <b>список трек-кодов</b> (каждый с новой строки) для проверки.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.check_single_code)
    logger.info(f"Пользователь {message.from_user.id} начал проверку трек-кодов.")


@track_code_search_router.message(TrackCodeStates.check_single_code)
async def process_track_code(message: Message, state: FSMContext) -> None:
    """Обрабатывает введённые пользователем трек-коды."""
    if message.text == "Отмена":
        await message.answer("Режим проверки трек-кодов завершён.", reply_markup=main_keyboard)
        await state.clear()
        logger.info(f"Пользователь {message.from_user.id} завершил проверку трек-кода.")
        return

    tg_id: int = message.from_user.id
    input_text: str = message.text.strip()

    # Используем re.findall для надежного извлечения всех кодов из любого текста
    track_codes: List[str] = re.findall(TRACK_CODE_PATTERN, input_text, re.IGNORECASE)

    # Удаляем дубликаты, сохраняя порядок (для Python 3.7+)
    track_codes = list(dict.fromkeys(track_codes))

    if not track_codes:
        await message.answer(
            "Не найдено корректных трек-кодов. Пожалуйста, введите код(ы) (минимум 8 букв/цифр).",
            reply_markup=cancel_keyboard
        )
        return

    is_single_code = len(track_codes) == 1

    if is_single_code:
        # --- ЛОГИКА ДЛЯ ОДНОГО КОДА (Подробное отображение) ---
        track_code_text = track_codes[0]
        try:
            track_info = await get_track_code_status(track_code_text)

            if track_info:
                status = track_info['status']
                owner_tg_id = track_info.get('tg_id')

                # Форматирование статуса и времени
                updated_at = "Неизвестно"  # Заглушка, т.к. поля нет в БД
                status_message = status_messages.get(status, "Статус неизвестен")

                # Определение принадлежности
                if owner_tg_id == tg_id:
                    ownership_status = "✅ Вы отслеживаете этот код"
                elif owner_tg_id is not None:
                    ownership_status = f"👤 Отслеживается другим пользователем (ID скрыт)"
                else:
                    ownership_status = "⚪️ Никем не отслеживается"

                response = (
                    f"🔎 <b>Результат поиска:</b>\n\n"
                    f"📦 Код: <code>{track_code_text}</code>\n"
                    f"ℹ️ Статус: <b>{status_message}</b>\n"
                    f"🔐 {ownership_status}\n"
                )
                await message.answer(response)
            else:
                await message.answer(
                    f"❌ Трек-код <code>{track_code_text}</code> не найден в системе.\n"
                    f"Используйте <code>Добавить трек-коды</code>, чтобы начать отслеживание."
                )

        except Exception as e:
            logger.error(f"Ошибка при проверке трек-кода {track_code_text}: {e}")
            await message.answer("Произошла ошибка при проверке. Попробуйте позже.")

    else:
        # --- ЛОГИКА ДЛЯ МНОЖЕСТВА КОДОВ (Краткое отображение с разбивкой) ---
        response_lines = [f"📦 <b>Результаты проверки ({len(track_codes)} шт.):</b>\n"]

        for track_code_text in track_codes:
            try:
                track_info = await get_track_code_status(track_code_text)
                if track_info:
                    status = track_info['status']
                    status_msg = status_messages.get(status, "Статус неизвестен")
                    response_lines.append(f"• <code>{track_code_text}</code> — <b>{status_msg}</b>")
                else:
                    response_lines.append(f"• <code>{track_code_text}</code> — ❌ Не найден")
            except Exception:
                response_lines.append(f"• <code>{track_code_text}</code> — ⚠️ Ошибка")

        full_response = "\n".join(response_lines)

        # Используем новую функцию для безопасной отправки длинного текста
        await send_chunked_response(message, full_response)

    # Всегда показываем предложение продолжить в конце
    await message.answer(
        "Отправьте следующий трек-код (или список) или нажмите '<b>Отмена</b>'.",
        reply_markup=cancel_keyboard
    )


# ************************************************
# 2. ПРОСМОТР СВОИХ ТРЕК-КОДОВ
# ************************************************

@track_code_search_router.callback_query(F.data == "my_track_codes")
async def view_my_track_codes(callback: CallbackQuery):
    """Отправляет пользователю список его трек-кодов (с разбивкой на части)."""
    await callback.message.delete()
    user_tg_id = callback.from_user.id
    track_codes = await get_user_track_codes(user_tg_id)

    if track_codes:
        response_lines = ["📋 <b>Ваши отслеживаемые трек-коды:</b>\n"]
        for my_track_code, status in track_codes:
            status_message = status_messages.get(status, "Неизвестный статус")
            response_lines.append(f"• <code>{my_track_code}</code> — <i>{status_message}</i>")

        full_response = "\n".join(response_lines)

        # Здесь тоже используем безопасную отправку, т.к. список может быть длинным
        await send_chunked_response(callback.message, full_response)

        # После списка показываем меню действий
        await callback.message.answer(
            "Что хотите сделать дальше?",
            reply_markup=add_track_codes_follow_up_keyboard
        )
    else:
        await callback.message.answer(
            "У вас нет отслеживаемых трек-кодов.\n"
            "Используйте <b>Добавить трек-коды</b>, чтобы они появились здесь.",
            reply_markup=add_track_codes_follow_up_keyboard
        )

    await callback.answer()


# ************************************************
# 3. ПЕРЕХОД К ПРОВЕРКЕ ТРЕК-КОДА (Через Inline-кнопку)
# ************************************************

@track_code_search_router.callback_query(F.data == "start_check_codes")
async def start_check_codes_from_follow_up(callback: CallbackQuery, state: FSMContext) -> None:
    """Запускает процесс проверки статуса трек-кода по нажатию Inline-кнопки."""
    await callback.message.delete()
    await callback.message.answer(
        "Вы перешли в режим проверки. Отправьте <b>трек-код</b> (или список) для проверки.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.check_single_code)
    await callback.answer()