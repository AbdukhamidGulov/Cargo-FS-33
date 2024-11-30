from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import update_user_info
from keyboards import main_keyboard

change = Router()

class UpdateInfoStates(StatesGroup):
    waiting_for_new_value = State()

@change.callback_query(F.data.startswith("change_"))
async def change_info(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    field = callback.data.split("_")[-1]  # (name, phone, address)
    d = {"name": "Введите новое имя:", "phone": "Введите новый номер телефона:", "address": "Введите новый адрес:"}
    await state.update_data(field=field)
    await state.set_state(UpdateInfoStates.waiting_for_new_value)
    await callback.message.answer(d[field])

@change.message(UpdateInfoStates.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    new_value = message.text
    data = await state.get_data()
    field = data.get("field")
    await update_user_info(message.from_user.id, field, new_value)
    await state.clear()
    await message.answer("Успешно обновлено.", reply_markup=main_keyboard)
