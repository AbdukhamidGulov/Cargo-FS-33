from aiogram import Router, F
from aiogram.types import CallbackQuery

from calculator.calc_keyboards import calc_back_menu_keyboard

calc_shipping = Router()

@calc_shipping.callback_query(F.data == "calc_shipping")
async def calculate_volume(callback: CallbackQuery):  # , state: FSMContext
    await callback.message.delete()
    await callback.message.answer("Эта функция ещё не реализованна", reply_markup=calc_back_menu_keyboard)
