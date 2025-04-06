from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from logging import getLogger

from database.track_codes import check_or_add_track_code, get_user_track_codes
from keyboards import main_keyboard, cancel_keyboard

track_code_router = Router()
logger = getLogger(__name__)


status_messages = {
    "in_stock": "Ваш товар уже на складе.",
    "out_of_stock": "Ваш товар ещё не прибыл на склад.",
    "shipped": "Ваш товар был отправлен."
}


class TrackCodeStates(StatesGroup):
    track_code = State()

@track_code_router.message(F.text == "Проверка трек-кода")
async def check_track_code(message: Message, state: FSMContext) -> None:
    """Запускает процесс проверки трек-кода, запрашивая у пользователя трек-код."""
    await message.answer("Отправьте ваш трек-код для проверки:")
    await state.set_state(TrackCodeStates.track_code)
    logger.info(f"Пользователь {message.from_user.id} начал проверку трек-кода.")

@track_code_router.message(TrackCodeStates.track_code)
async def process_track_code(message: Message, state: FSMContext) -> None:
    """Обрабатывает введённый пользователем трек-код, проверяет его статус и отправляет ответ."""
    if message.text == "Отмена":
        await message.answer("Режим проверки трек-кодов завершён.", reply_markup=main_keyboard)
        await state.clear()
        logger.info(f"Пользователь {message.from_user.id} завершил проверку трек-кода.")
        return

    tg_id: int = message.from_user.id
    track_code_text: str = message.text.strip()

    # Проверка валидности трек-кода
    if not track_code_text:
        await message.answer("Трек-код не может быть пустым.")
        logger.warning(f"Пользователь {tg_id} отправил пустой трек-код.")
    else:
        try:
            status = await check_or_add_track_code(track_code_text, tg_id)
            response = status_messages.get(status, "Статус трек-кода неизвестен. Обратитесь к администратору.")
            await message.answer(response)
            logger.info(f"Пользователь {tg_id} проверил трек-код {track_code_text}: статус {status}")
        except Exception as e:
            logger.error(f"Ошибка при обработке трек-кода {track_code_text} для пользователя {tg_id}: {e}")
            await message.answer("Произошла ошибка при проверке трек-кода. Попробуйте позже или обратитесь к администратору.")

    await message.answer(
        "Вы можете отправить следующий <b>трек-код</b> или нажать '<code>Отмена</code>', чтобы завершить проверку.",
        reply_markup=cancel_keyboard
    )


@track_code_router.callback_query(F.data == "my_track_codes")
async def my_track_codes(callback: CallbackQuery):
    """Отправляет пользователю список его трек-кодов."""
    await callback.message.delete()
    user_tg_id = callback.from_user.id
    track_codes = await get_user_track_codes(user_tg_id)
    if track_codes:
        response = "Ваши трек-коды:\n\n"
        for my_track_code, status in track_codes:
            status_message = status_messages.get(status, "Не на складе")
            response += f"<b>{my_track_code}</b> - <i>{status_message}</i>\n"
        await callback.message.answer(response)
    else:
        await callback.message.answer(
            "У вас нет зарегистрированных трек-кодов.\n"
            "Для того чтобы их добавить, просто поищите их через команду "
            "<code>Проверка трек-кода</code> и они автоматически сохранятся в ваши трек-коды"
        )
