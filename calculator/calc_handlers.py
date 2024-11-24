from aiogram import F, Router
from aiogram.types import CallbackQuery

from calculator.calc_keyboards import calc_main_menu_keyboard

calc = Router()


@calc.callback_query(F.data == "calculator")
async def calculator(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Что хотите рассчитать?", reply_markup=calc_main_menu_keyboard)


#
# @calc_volume.callback_query(F.data == "calculate_shipping")
# async def calculate_shipping(callback: CallbackQuery):
#     await callback.message.answer("?", reply_markup=calc_main_menu_keyboard)
#
