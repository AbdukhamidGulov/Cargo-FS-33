from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from database.db_users import get_info_profile, update_user_info
from keyboards import my_profile_keyboard, change_data_keyboard, main_keyboard
from registration_process import PHONE_VALIDATION_ERROR, ERROR_MESSAGE

profile_router = Router()
logger = getLogger(__name__)

@profile_router.callback_query(F.data == "my_profile")
async def profile(callback: CallbackQuery):
    """Отправляет пользователю информацию о его профиле."""
    await callback.message.delete()
    inf = await get_info_profile(callback.from_user.id)
    if not inf:
        await callback.message.answer("Профиль не найден.")
        return
    no = "<i>Не заполнено</i>"
    await callback.message.answer(
        f"Номер для заказов: <code>FS{inf.get('id'):04d}</code>\n"
        f"Имя: {inf.get('name') or no}\n"
        f"Номер: {inf.get('phone') or no}\n"
    )
    await callback.message.answer("Что нужно сделать ещё?", reply_markup=my_profile_keyboard)


# --- Процесс изменения данных профиля ---

@profile_router.callback_query(F.data == "change_profile_data")
async def change_profile_data(callback: CallbackQuery):
    """Запускает процесс изменения данных профиля."""
    await callback.message.delete()
    await callback.message.answer("Что хотите изменить?", reply_markup=change_data_keyboard)


class UpdateInfoStates(StatesGroup):
    waiting_for_new_value = State()

@profile_router.callback_query(F.data.startswith("change_"))
async def start_field_update(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс изменения данных пользователя, запрашивая новое значение."""
    await callback.message.delete()
    target_field = callback.data.split("_")[-1]  # "name" или "phone"
    field_prompts = {
        "name": "Введите новое имя:",
        "phone": "Введите новый номер телефона:"
    }
    await state.update_data(field=target_field)
    await state.set_state(UpdateInfoStates.waiting_for_new_value)
    await callback.message.answer(field_prompts[target_field])

@profile_router.message(UpdateInfoStates.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    """Обрабатывает введённое пользователем новое значение и обновляет данные."""
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
    except ValueError as e:
        logger.error(f"Ошибка при обновлении {target_field} для пользователя {message.from_user.id}: {e}")
        await message.answer(ERROR_MESSAGE)
    finally:
        await state.clear()
