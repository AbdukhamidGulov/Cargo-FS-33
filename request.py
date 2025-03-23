from logging import getLogger

from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from filters_and_config import admin_ids
from keyboards import get_main_inline_keyboard

request_router = Router()
logger = getLogger(__name__)

class RequestVerification(StatesGroup):
    waiting_for_track_codes = State()

@request_router.callback_query(F.data == "request_for_verification")
async def start_verification_request(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс подачи заявки на проверку товаров."""
    await callback.message.delete()
    await callback.message.answer(
        "Эта команда предназначена для подачи заявок на проверку товаров. "
        "Пожалуйста, отправьте все трек-коды одним сообщением, разделяя их пробелами или переносами строки."
    )
    await state.set_state(RequestVerification.waiting_for_track_codes)

@request_router.message(RequestVerification.waiting_for_track_codes)
async def receive_track_codes(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает введённые пользователем трек-коды и отправляет их администратору."""
    track_code_list = message.text.strip().split()  # Получаем список трек-кодов

    if not track_code_list:
        await message.answer("Вы не указали ни одного трек-кода. Пожалуйста, попробуйте снова.")
        return

    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"

    admin_notification = (
        f"Пользователь <b>{username}</b> (ID: <code>{user_id}</code>) "
        "оставил заявку на проверку своих товаров.\n\n"
        f"Трек-коды:\n{chr(10).join(track_code_list)}"
    )

    try:
        await bot.send_message(chat_id=admin_ids[1], text=admin_notification)
        await message.answer(
            "Ваша заявка на проверку товаров успешно отправлена администратору.",
            reply_markup=get_main_inline_keyboard(message.from_user.id)
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки администратору: {e}")
        await message.answer(
            "Произошла ошибка при отправке заявки. Попробуйте позже или обратитесь к администратору."
        )
    finally:
        await state.clear()
