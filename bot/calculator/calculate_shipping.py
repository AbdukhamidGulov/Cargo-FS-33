import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_keyboard

calc_shipping_router = Router()

@calc_shipping_router.callback_query(F.data == "calc_shipping_router")  # Не задействована
async def calculate_volume(callback: CallbackQuery):  # , state: FSMContext
    await callback.message.delete()
    await callback.message.answer("Эта функция ещё не реализованна", reply_markup=main_keyboard)


# Не обработанные хендлерамы
@calc_shipping_router.message(F.text)
async def end_text_handler(message: Message):
    await message.answer(f'Кнопка <code>"{message.text}"</code> не попала в функции! Напишите администратору!')
    logging.debug(f'Кнопка "{message.text}" не попала в функции!')


@calc_shipping_router.message(F.data)
async def end_data_handler(callback: CallbackQuery):
    await callback.message.answer(f'Кнопка <code>"{callback.message.text}"</code> не попала в функции! Напишите администратору!')
    logging.debug(f'Кнопка "{callback.message.text}" не попала в функции!')
