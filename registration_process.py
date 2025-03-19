from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from database.users import add_user_info
from keyboards import main_keyboard

states = Router()
logger = getLogger(__name__)

class Registration(StatesGroup):
    name = State()
    number = State()

async def send_welcome_messages(message: Message, user_id: int):
    """Отправляет приветственные сообщения пользователю после регистрации.

    :param message: Объект сообщения от пользователя.
    :param user_id: ID нового пользователя в базе данных.
    """
    await message.answer("Спасибо за регистрацию!")
    await message.answer(f"Ваш персональный номер для совершения заказов: <code>FS{user_id:04d}</code>")
    await message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)

@states.callback_query(F.data == "do_reg")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс регистрации, запрашивая имя и фамилию.

    :param callback: Объект callback-запроса.
    :param state: Контекст FSM для управления состояниями.
    """
    await callback.message.delete()
    await state.set_state(Registration.name)
    await callback.message.answer("Введите ваше Имя и Фамилию пожалуйста:")


ERROR_MESSAGE = "Произошла ошибка при обновлении данных. Попробуйте позже или обратитесь к администратору."
PHONE_VALIDATION_ERROR = ("Пожалуйста, введите корректный номер телефона. Используйте только цифры, "
                          "знак '+' в начале (если нужно) или '-' для разделения (например, +79991234567 или 8-999-123-45-67).")


@states.message(Registration.name)
async def process_user_name(message: Message, state: FSMContext):
    """Обрабатывает введённое имя пользователя и запрашивает номер телефона.

    :param message: Объект сообщения от пользователя.
    :param state: Контекст FSM для управления состояниями.
    """
    user_name = message.text.title()
    await state.update_data(name=user_name)
    await state.set_state(Registration.number)
    await message.answer("Напишите номер вашего телефона пожалуйста:")

@states.message(Registration.number)
async def process_user_number(message: Message, state: FSMContext):
    """Обрабатывает введённый номер телефона и завершает регистрацию.

    :param message: Объект сообщения от пользователя.
    :param state: Контекст FSM для управления состояниями.
    """
    phone_number = message.text.strip()
    # Базовая проверка номера телефона
    if not all(c.isdigit() or c in "+-" for c in phone_number):
        await message.answer("Пожалуйста, введите корректный номер телефона (только цифры, + или -).")
        return

    await state.update_data(number=phone_number)
    user_data = await state.get_data()
    await state.clear()

    try:
        new_user = await add_user_info(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            name=user_data["name"],
            phone=user_data["number"]
        )
        await send_welcome_messages(message, new_user["id"])
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {message.from_user.id}: {e}")
        await message.answer(PHONE_VALIDATION_ERROR)

@states.callback_query(F.data == "pass_reg")
async def skip_registration(callback: CallbackQuery):
    """Обрабатывает пропуск регистрации, используя данные из Telegram.

    :param callback: Объект callback-запроса.
    """
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name or "Не указано"
    username = callback.from_user.username

    try:
        new_user = await add_user_info(tg_id=user_id, username=username, name=first_name)
        await callback.message.delete()
        await send_welcome_messages(callback.message, new_user["id"])
    except Exception as e:
        logger.error(f"Ошибка при пропуске регистрации для пользователя {user_id}: {e}")
        await callback.message.answer(ERROR_MESSAGE)
