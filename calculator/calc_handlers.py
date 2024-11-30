from aiogram import F, Router
from aiogram.types import Message

from calculator.calc_keyboards import calc_main_menu_keyboard

calc = Router()


@calc.message(F.text == "Рассчитать стоимость 💸")
async def calculator(message: Message):
    await message.delete()
    await message.answer("Что хотите рассчитать?", reply_markup=calc_main_menu_keyboard)


#
# @calc_volume.callback_query(F.data == "calc_shipping")
# async def calc_shipping(callback: CallbackQuery):
#     await callback.message.answer("?", reply_markup=calc_main_menu_keyboard)
#
