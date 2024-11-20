from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from aiogram import Router, F

from database import add_user_info
from keyboards import main_keyboard

states = Router()


class Registration(StatesGroup):
    name = State()
    number = State()
    city = State()

@states.callback_query(F.data == "do_reg")
async def registration_process(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.set_state(Registration.name)
    await callback.message.answer("Введите ваше Имя и Фамилию пожалуйста:")

@states.message(Registration.name)
async def add_user_name(message: Message, state: FSMContext):
    user_name = message.text.title()
    await state.update_data(name=user_name)
    await state.set_state(Registration.number)
    await message.answer("Напишите номер вашего телефона пожалуйста:")

@states.message(Registration.number)
async def add_user_name(message: Message, state: FSMContext):
    await state.update_data(number = message.text)
    await state.set_state(Registration.city)
    await message.answer("Напишите ваш адрес пожалуйста:")

@states.message(Registration.city)
async def add_user_name(message: Message, state: FSMContext):
    user_city = message.text.title()
    await state.update_data(city = user_city)
    data = await state.get_data()
    await state.clear()
    new_user_id = await add_user_info(message.from_user.id, message.from_user.username,
                                      data["name"], data["number"], data["city"])
    await message.answer("Спасибо за регистрацию!")
    personal_number = f"FS{new_user_id:04d}"
    await message.answer(
        f"Ваш персональный номер для совершения заказов: <code>{personal_number}</code>\nСохраните его где-нибудь.")
    await message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)


# Функция для получении данных с телеграмма, если пользователь нажмёт "Пропустит"
@states.callback_query(F.data == "pass_reg")
async def pass_reg(callback: CallbackQuery):
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name
    username = callback.from_user.username
    await callback.message.delete()
    await add_user_info(user_id, username, first_name)
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)


@states.message()
async def send_echo(message: Message):
    await message.answer('Простите! Введена неверная команда')
