from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from filters_and_config import admin_ids
from keyboards import get_main_inline_keyboard

request = Router()


class RequestVerification(StatesGroup):
    waiting_for_track_codes = State()


@request.callback_query(F.data == "request_for_verification")
async def start_verification_request(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Эта команда предназначена для подачи заявок на проверку товаров. "
        "Пожалуйста, отправьте все трек-коды одним сообщением, разделяя их пробелами или переносами строки."
    )
    await state.set_state(RequestVerification.waiting_for_track_codes)


# Функция для получения трек-кодов
@request.message(RequestVerification.waiting_for_track_codes)
async def receive_track_codes(message: Message, state: FSMContext, bot: Bot):
    track_codes = message.text.strip().split()  # Получаем список трек-кодов
    user_id = message.from_user.id  # ID пользователя
    username = message.from_user.username  # Имя пользователя (если указано)

    admin_message = (
        f"Пользователь <b>{username or 'Без имени'}</b> (ID: <code>{user_id}</code>) "
        "оставил заявку на проверку своих товаров.\n\n"
        f"Трек-коды:\n{chr(10).join(track_codes)}"
    )
    await bot.send_message(chat_id=admin_ids[1]  , text=admin_message)
    await message.answer("Ваша заявка на проверку товаров успешно отправлена администратору.",
                         reply_markup=get_main_inline_keyboard(message.from_user.id))
    await state.clear()