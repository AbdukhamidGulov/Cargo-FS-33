from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from keyboards import main_keyboard

calc_volume = Router()

class CargoCalculator(StatesGroup):
    length = State()  # длина
    width = State()   # ширина
    height = State()  # высота
    weight = State()  # вес


@calc_volume.callback_query(F.data == "calculate_volume")
async def calculate_volume(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer_photo(
        "AgACAgIAAxkBAAIC12dDODeR9pB6wB0FwZo7yPjFQ4p_AALe5zEbF8_QSXw4G3IYnu6FAQADAgADcwADNgQ",
        "❗️<i>Что такое плотность и для чего она нужна? "
        "<a href='https://t.me/quicktao_cargo1/16303'>Читайте здесь</a></i>\n\n"
        "Для расчёта плотности груза введите длину груза (в сантиметрах):")
    await state.set_state(CargoCalculator.length)

# Обработка длины
@calc_volume.message(CargoCalculator.length)
async def input_length(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение длины.")
    else:
        await state.update_data(length=int(message.text))
        await message.answer_photo(
            "AgACAgIAAxkBAAIC22dDPTTeZGmoebUNiAnw1DeBaRS5AALg5zEbF8_QSVQaSQKyc8t1AQADAgADcwADNgQ",
                                   "Введите ширину упаковки (в сантиметрах):")
        await state.set_state(CargoCalculator.width)

# Обработка ширины
@calc_volume.message(CargoCalculator.width)
async def input_width(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение ширины.")
    else:
        await state.update_data(width=int(message.text))
        await message.answer_photo(
            "AgACAgIAAxkBAAIC3WdDPbKq8yf1XCDVJtaBU0r_3Jx5AALf5zEbF8_QSZaf5vQCjiBIAQADAgADcwADNgQ",
            "Введите высоту упаковки (в сантиметрах):")
        await state.set_state(CargoCalculator.height)

# Обработка высоты
@calc_volume.message(CargoCalculator.height)
async def input_height(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение высоты.")
    else:
        await state.update_data(height=int(message.text))
        await message.answer_photo(
            "AgACAgIAAxkBAAIC32dDPfbEGlPi_7kc3Q5agF6LuaKGAALh5zEbF8_QSV_BwbvNnOLsAQADAgADcwADNgQ",
            "Теперь введите вес груза (в килограммах):")
        await state.set_state(CargoCalculator.weight)

# Обработка веса и вывод результата
@calc_volume.message(CargoCalculator.weight)
async def input_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        data = await state.get_data()
        volume = data["length"] * data["width"] * data["height"] / 1000000
        density = weight / volume

        await message.answer_photo(
            "AgACAgIAAxkBAAIDEmdDRPPKCM_q0ZJ49T9-5h1z9f7LAALR5zEbI2PQSQZ_9fnuXY76AQADAgADcwADNgQ",
            f"Объём груза: {volume:.2f} м³\n"
            f"Плотность груза: {density:.2f} кг/м³", reply_markup=main_keyboard)
        await state.clear()
    except ValueError:
        await message.answer("Введите числовое значение веса.")

# # Обработка кнопок
# @calc_volume.callback_query(F.data == "main_menu")
# async def main_menu(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Вы вернулись в главное меню.")
#     await state.clear()
#
# @calc_volume.callback_query(F.data == "back")
# async def go_back(callback: CallbackQuery, state: FSMContext):
#     current_state = await state.get_state()
#     if current_state == CargoCalculator.weight:
#         await callback.message.answer("Введите высоту груза (в сантиметрах):")
#         await state.set_state(CargoCalculator.height)
#     elif current_state == CargoCalculator.height:
#         await callback.message.answer("Введите ширину груза (в сантиметрах):")
#         await state.set_state(CargoCalculator.width)
#     elif current_state == CargoCalculator.width:
#         await callback.message.answer("Введите длину груза (в сантиметрах):")
#         await state.set_state(CargoCalculator.length)
#     else:
#         await callback.message.answer("Вы уже в начальном состоянии.")
