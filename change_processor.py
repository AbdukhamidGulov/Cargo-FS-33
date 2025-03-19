from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.users import update_user_info
from keyboards import main_keyboard
from registration_process import ERROR_MESSAGE, PHONE_VALIDATION_ERROR

change = Router()
logger = getLogger(__name__)

class UpdateInfoStates(StatesGroup):
    waiting_for_new_value = State()

@change.callback_query(F.data.startswith("change_"))
async def start_field_update(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс изменения данных пользователя, запрашивая новое значение.

    :param callback: Объект callback-запроса.
    :param state: Контекст FSM для управления состояниями.
    """
    await callback.message.delete()
    target_field = callback.data.split("_")[-1]  # "name" или "phone"
    field_prompts = {
        "name": "Введите новое имя:",
        "phone": "Введите новый номер телефона:"
    }
    await state.update_data(field=target_field)
    await state.set_state(UpdateInfoStates.waiting_for_new_value)
    await callback.message.answer(field_prompts[target_field])

@change.message(UpdateInfoStates.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    """Обрабатывает введённое пользователем новое значение и обновляет данные.

    :param message: Объект сообщения от пользователя.
    :param state: Контекст FSM для управления состояниями.
    """
    new_value = message.text.strip()
    state_data = await state.get_data()
    target_field = state_data.get("field")

    # Валидация номера телефона
    if target_field == "phone":
        if not all(c.isdigit() or c in "+-" for c in new_value):
            await message.answer(PHONE_VALIDATION_ERROR)
            return

    try:
        await update_user_info(tg_id=message.from_user.id, field=target_field, value=new_value)
        field_names = {"name": "Имя", "phone": "Номер телефона"}
        await message.answer(f"{field_names[target_field]} успешно обновлено.", reply_markup=main_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обновлении {target_field} для пользователя {message.from_user.id}: {e}")
        await message.answer(ERROR_MESSAGE)
    finally:
        await state.clear()
