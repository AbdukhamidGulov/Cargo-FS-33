import re
from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.track_codes import get_track_code_status, get_user_track_codes
from keyboards import main_keyboard, cancel_keyboard, add_track_codes_follow_up_keyboard

# Импорт необходимых констант и состояний из основного файла track_numbers.
# Убедитесь, что track_numbers.py импортируется в main.py до track_codes_search.py
# или что в track_numbers.py содержится определение всех нужных констант.
from track_numbers import TRACK_CODE_PATTERN, status_messages, TrackCodeStates

track_code_search_router = Router()
logger = getLogger(__name__)


# ************************************************
# 1. ПРОВЕРКА ОДНОГО ТРЕК-КОДА (Подробное отображение)
# ************************************************

@track_code_search_router.message(F.text.lower() == "проверка трек-кодов")
async def check_track_code(message: Message, state: FSMContext) -> None:
    """Запускает процесс проверки статуса трек-кода."""
    await message.answer(
        "Отправьте ваш <b>трек-код</b> для проверки.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.check_single_code)
    logger.info(f"Пользователь {message.from_user.id} начал проверку трек-кода.")


@track_code_search_router.message(TrackCodeStates.check_single_code)
async def process_track_code(message: Message, state: FSMContext) -> None:
    """Обрабатывает введённый пользователем трек-код, проверяет его статус и выводит подробную информацию."""
    if message.text == "Отмена":
        await message.answer("Режим проверки трек-кодов завершён.", reply_markup=main_keyboard)
        await state.clear()
        logger.info(f"Пользователь {message.from_user.id} завершил проверку трек-кода.")
        return

    tg_id: int = message.from_user.id
    track_code_text: str = message.text.strip()

    # ПРОВЕРКА ВАЛИДНОСТИ ТРЕК-КОДА
    if not re.fullmatch(TRACK_CODE_PATTERN, track_code_text, re.IGNORECASE):
        await message.answer(
            f"Формат <code>{track_code_text}</code> не похож на трек-код. "
            f"Пожалуйста, введите корректный код (минимум 8 букв/цифр).",
            reply_markup=cancel_keyboard
        )
        return

    try:
        # track_info должен содержать: status, tg_id (владелец)
        track_info = await get_track_code_status(track_code_text)

        if track_info:
            # Трек-код найден
            status = track_info['status']

            # ИСПРАВЛЕНИЕ: Используем ключ 'tg_id' вместо 'user_id'
            owner_tg_id = track_info.get('tg_id', 'Н/Д')

            # В базе данных нет полей updated_at, поэтому его пока убираем или оставляем "Неизвестно"
            updated_at = "Неизвестно (обновляется при смене статуса)"

            status_message = status_messages.get(status, "Статус трек-кода неизвестен. Обратитесь к администратору.")

            # Определение принадлежности
            ownership_status = "Н/Д (не отслеживается)"
            if owner_tg_id != 'Н/Д' and owner_tg_id is not None:
                if owner_tg_id == tg_id:
                    ownership_status = "✅ Вы отслеживаете этот код"
                else:
                    ownership_status = f"👤 Отслеживается другим пользователем (ID: <code>{owner_tg_id}</code>)"

            # Улучшенное и подробное отображение для одного трек-кода
            response = (
                f"🔎 <b>Результаты поиска трек-кода:</b>\n\n"
                f"  Код: <code>{track_code_text}</code>\n"
                f"  Статус: <b>{status_message}</b>\n"
                f"  Отслеживание: {ownership_status}\n"
                f"  Последнее обновление: <i>{updated_at}</i>\n"
            )

            await message.answer(response)
            logger.info(f"Пользователь {tg_id} проверил трек-код {track_code_text}: статус {status}")
        else:
            # Трек-код не найден
            await message.answer(
                f"Трек-код <code>{track_code_text}</code> не найден в нашей системе.\n\n"
                f"Если вы хотите <b>начать его отслеживать</b>, воспользуйтесь командой <code>Добавить трек-коды</code>."
            )
            logger.info(f"Пользователь {tg_id} проверил несуществующий трек-код {track_code_text}.")

    except Exception as e:
        logger.error(f"Ошибка при обработке трек-кода {track_code_text} для пользователя {tg_id}: {e}")
        await message.answer(
            "Произошла ошибка при проверке трек-кода. Попробуйте позже или обратитесь к администратору.")

    await message.answer(
        "Вы можете отправить следующий <b>трек-код</b> или нажать '<code>Отмена</code>', чтобы завершить проверку.",
        reply_markup=cancel_keyboard
    )


# ************************************************
# 2. ПРОСМОТР СВОИХ ТРЕК-КОДОВ (Старая логика, теперь будет заменена на проверку)
# ************************************************

@track_code_search_router.callback_query(F.data == "my_track_codes")
async def view_my_track_codes(callback: CallbackQuery):
    """Отправляет пользователю список его трек-кодов."""
    await callback.message.delete()
    user_tg_id = callback.from_user.id
    track_codes = await get_user_track_codes(user_tg_id)

    if track_codes:
        response = "<b>Ваши отслеживаемые трек-коды:</b>\n\n"
        for my_track_code, status in track_codes:
            # Используем status_messages для получения более понятного статуса
            status_message = status_messages.get(status, "Неизвестный статус")
            response += f"• <code>{my_track_code}</code> - <i>{status_message}</i>\n"
        await callback.message.answer(response)
    else:
        await callback.message.answer(
            "У вас нет зарегистрированных трек-кодов.\n"
            "Чтобы добавить их, воспользуйтесь командой <code>Добавить трек-кода</code>.",
            reply_markup=add_track_codes_follow_up_keyboard
        )

    await callback.answer()  # Убираем 'часики'


# ************************************************
# 3. ПЕРЕХОД К ПРОВЕРКЕ ТРЕК-КОДА (Через Inline-кнопку)
# ************************************************

@track_code_search_router.callback_query(F.data == "start_check_codes")
async def start_check_codes_from_follow_up(callback: CallbackQuery, state: FSMContext) -> None:
    """Запускает процесс проверки статуса трек-кода по нажатию Inline-кнопки."""
    await callback.message.delete()  # Удаляем предыдущее сообщение с кнопками

    await callback.message.answer(
        "Вы перешли в режим проверки трек-кодов. Отправьте <b>трек-код</b> для проверки.",
        reply_markup=cancel_keyboard
    )
    # Устанавливаем состояние для обработки следующего сообщения как единичного трек-кода
    await state.set_state(TrackCodeStates.check_single_code)
    logger.info(f"Пользователь {callback.from_user.id} начал проверку трек-кода через follow-up кнопку.")
    await callback.answer()
