from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import logging

from database.track_codes import check_or_add_track_code
from keyboards import main_keyboard, cancel_keyboard

track_code = Router()
logger = logging.getLogger(__name__)

# Определение состояний для FSM
class TrackCodeStates(StatesGroup):
    track_code = State()

@track_code.message(F.text == "Проверка трек-кода")
async def check_track_code(message: Message, state: FSMContext) -> None:
    """
    Запускает процесс проверки трек-кода, запрашивая у пользователя трек-код.

    Args:
        message (Message): Объект сообщения от пользователя.
        state (FSMContext): Контекст FSM для управления состояниями.
    """
    await message.answer("Отправьте ваш трек-код для проверки:")
    await state.set_state(TrackCodeStates.track_code)
    logger.info(f"Пользователь {message.from_user.id} начал проверку трек-кода.")

@track_code.message(TrackCodeStates.track_code)
async def process_track_code(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает введённый пользователем трек-код, проверяет его статус и отправляет ответ.

    Args:
        message (Message): Объект сообщения от пользователя.
        state (FSMContext): Контекст FSM для управления состояниями.

    Raises:
        Exception: Если произошла ошибка при проверке или добавлении трек-кода.
    """
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
            status_messages = {
                "in_stock": "Ваш товар уже на складе.",
                "out_of_stock": "Ваш товар ещё не прибыл на склад.",
                "shipped": "Ваш товар был отправлен."
            }
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
