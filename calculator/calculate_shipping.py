from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from keyboards import main_keyboard

calc_shipping = Router()

@calc_shipping.callback_query(F.data == "calc_shipping")  # Не задействована
async def calculate_volume(callback: CallbackQuery):  # , state: FSMContext
    await callback.message.delete()
    await callback.message.answer("Эта функция ещё не реализованна", reply_markup=main_keyboard)


# Не обработанные хендлерамы
@calc_shipping.message(F.text)
async def end_text_handler(message: Message):
    await message.answer(message.text)
    print(message.text)


@calc_shipping.message(F.data)
async def end_data_handler(callback: CallbackQuery):
    await callback.message.answer(callback.message.text)
    print(callback.message.text)