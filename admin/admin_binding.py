from logging import getLogger

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from database.db_track_codes import get_track_code_info, bulk_assign_track_codes
from database.db_users import get_user_by_id
from keyboards import cancel_keyboard, main_keyboard
from filters_and_config import IsAdmin, admin_ids
from utils.message_common import extract_text_from_message

admin_bulk_router = Router()
logger = getLogger(__name__)


class BindTrackStates(StatesGroup):
    """Состояния для массовой привязки трек-кодов."""
    waiting_for_track_codes = State()
    waiting_for_user_id = State()


# ************************************************************
# МАССОВАЯ ПРИВЯЗКА ТРЕК-КОДОВ К ПОЛЬЗОВАТЕЛЮ
# ************************************************************

@admin_bulk_router.message(F.text == "Массовая привязка трек-кодов", IsAdmin(admin_ids))
async def start_bulk_bind_tracks(message: Message, state: FSMContext, bot: Bot):  # Добавлен bot
    """Начинает процесс массовой привязки трек-кодов к пользователю."""
    await message.answer(
        "📦 <b>Массовая привязка трек-кодов</b>\n\n"
        "Отправьте список трек-кодов:\n"
        "• Можно отправить **текстом** (каждый код с новой строки).\n"
        "• Можно отправить **файлом (.txt)**.\n\n"
        "<i>Пример:</i>\n"
        "<code>YT1234567890123\nYT9876543210987</code>",
        reply_markup=cancel_keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BindTrackStates.waiting_for_track_codes)


@admin_bulk_router.message(BindTrackStates.waiting_for_track_codes, F.text.lower() == "отмена")
async def cancel_bulk_bind(message: Message, state: FSMContext, bot: Bot):  # Добавлен bot
    """Отменяет режим массовой привязки."""
    await message.answer("Массовая привязка отменена.", reply_markup=main_keyboard)
    await state.clear()


@admin_bulk_router.message(BindTrackStates.waiting_for_track_codes)
async def process_track_codes_for_binding(message: Message, state: FSMContext, bot: Bot):  # Добавлен bot
    """
    Обрабатывает список трек-кодов для массовой привязки, используя extract_text_from_message
    для поддержки текста и файлов.
    """
    # ИСПРАВЛЕНИЕ: Передаем bot, который требуется утилите для скачивания файлов.
    extraction_result = await extract_text_from_message(message, bot)

    track_codes = extraction_result.get('items', [])
    error_message = extraction_result.get('error')

    if error_message:
        # Если произошла ошибка при извлечении (например, файл слишком большой или неверный формат)
        await message.answer(f"❌ Ошибка извлечения данных:\n{error_message}",
                             reply_markup=cancel_keyboard)
        return

    # Проверяем, что список не пуст после извлечения
    if not track_codes:
        await message.answer(
            "❌ Не найдено трек-кодов для привязки.\n"
            "Пожалуйста, отправьте список или .txt файл.",
            reply_markup=cancel_keyboard
        )
        return

    total_codes = len(track_codes)
    await message.answer(f"⏳ Начинаю проверку {total_codes} трек-кодов в базе данных...")

    # Проверяем существование трек-кодов
    valid_track_codes = []
    invalid_track_codes = []

    for i, track_code in enumerate(track_codes):
        track_info = await get_track_code_info(track_code)
        if track_info:
            valid_track_codes.append((track_code, track_info['status']))
        else:
            invalid_track_codes.append(track_code)

    if not valid_track_codes:
        await message.answer(
            "❌ Ни один из трек-кодов не найден в базе данных.\n"
            "Проверьте правильность ввода и попробуйте снова.",
            reply_markup=cancel_keyboard
        )
        return

    # Сохраняем данные в состоянии
    await state.update_data({
        'valid_track_codes': valid_track_codes,
        'invalid_track_codes': invalid_track_codes
    })

    # Формируем сообщение с результатами проверки
    response = (
        f"✅ <b>Результат проверки</b>\n"
        f"Всего получено: <b>{total_codes}</b>\n"
        f"Найдено в базе: <b>{len(valid_track_codes)}</b>\n"
    )

    if invalid_track_codes:
        response += f"❌ Не найдено: <b>{len(invalid_track_codes)}</b>\n\n"
        response += "<i>Первые 10 не найденных:</i>\n<code>" + "\n".join(invalid_track_codes[:10]) + "</code>"
        if len(invalid_track_codes) > 10:
            response += f"\n... и еще {len(invalid_track_codes) - 10}"

    response += "\n\nТеперь введите ID пользователя (FSXXXX или число) для привязки:"

    await message.answer(response, reply_markup=cancel_keyboard, parse_mode="HTML")
    await state.set_state(BindTrackStates.waiting_for_user_id)


@admin_bulk_router.message(BindTrackStates.waiting_for_user_id)
async def process_user_id_for_bulk_binding(message: Message, state: FSMContext, bot: Bot):  # Добавлен bot
    """Обрабатывает ID пользователя для массовой привязки."""
    # Обработчик отмены, если пользователь передумал
    if message.text.lower() == "отмена":
        await message.answer("Массовая привязка отменена.", reply_markup=main_keyboard)
        await state.clear()
        return

    data = await state.get_data()
    valid_track_codes = data.get('valid_track_codes', [])
    invalid_track_codes = data.get('invalid_track_codes', [])

    user_id_str = message.text.strip()

    # Парсим ID пользователя
    user_id = None
    if user_id_str.startswith("FS"):
        numeric_part = user_id_str[2:]
        if numeric_part.isdigit():
            user_id = int(numeric_part)
    elif user_id_str.isdigit():
        user_id = int(user_id_str)

    if not user_id:
        await message.answer(
            "❌ Неверный формат ID. Введите FSXXXX или число.",
            reply_markup=cancel_keyboard
        )
        return

    # Получаем данные пользователя
    user_data = await get_user_by_id(user_id)
    if not user_data:
        await message.answer(
            f"❌ Пользователь с ID <code>FS{user_id:04d}</code> не найден.",
            reply_markup=cancel_keyboard
        )
        return

    await message.answer(
        f"🔗 Начинаю привязку {len(valid_track_codes)} трек-кодов к пользователю <code>FS{user_id:04d}</code>...")

    # Массовая привязка трек-кодов
    success_count = 0
    failed_track_codes = []

    user_name = user_data.get('name', 'Неизвестно')

    for track_code, _ in valid_track_codes:
        # Убедимся, что user_data['tg_id'] существует
        tg_id = user_data.get('tg_id')
        if not tg_id:
            logger.error(f"User data for internal ID {user_id} is missing tg_id!")
            failed_track_codes.append(track_code)
            continue

        success = await bulk_assign_track_codes(track_code, tg_id)
        if success:
            success_count += 1
        else:
            failed_track_codes.append(track_code)

    # Формируем итоговое сообщение
    response = (
        f"📊 <b>Результаты массовой привязки</b>\n\n"
        f"👤 Пользователь: <code>FS{user_id:04d}</code> ({user_name})\n"
        f"✅ Успешно привязано: <b>{success_count}</b> трек-кодов\n"
    )

    if failed_track_codes:
        response += f"❌ Ошибка привязки: <b>{len(failed_track_codes)}</b> трек-кодов\n"
        response += "<i>Не удалось привязать:</i>\n<code>" + "\n".join(failed_track_codes[:5]) + "</code>"
        if len(failed_track_codes) > 5:
            response += f"\n... и еще {len(failed_track_codes) - 5}"

    if invalid_track_codes:
        response += f"\n\n⚠️ <b>Не найдено в базе:</b> {len(invalid_track_codes)} трек-кодов"

    await message.answer(response, reply_markup=main_keyboard, parse_mode="HTML")
    await state.clear()