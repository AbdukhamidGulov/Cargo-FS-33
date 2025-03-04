from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from keyboards import main_keyboard, main_inline_keyboard
from text_info import calculate_volume_photo1, calculate_volume_photo5

calc_volume = Router()

class CargoCalculator(StatesGroup):
    length = State()  # длина
    width = State()   # ширина
    height = State()  # высота
    weight = State()  # вес


@calc_volume.message(F.text == "Рассчитать объём")
async def calculate_volume(message: Message, state: FSMContext):
    await message.delete()
    await message.answer_photo(
        calculate_volume_photo1, "❗️<i>Что такое плотность и для чего она нужна? "
        "<a href='https://t.me/cargoFS33/1426'>Читайте здесь</a></i>\n\n"
        "Для расчёта плотности груза введите длину груза (в сантиметрах):")
    await state.set_state(CargoCalculator.length)

# Обработка длины
@calc_volume.message(CargoCalculator.length)
async def input_length(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение длины.")
    else:
        await state.update_data(length=int(message.text))
        await message.answer_photo(calculate_volume_photo1, "Введите ширину упаковки (в сантиметрах):")
        await state.set_state(CargoCalculator.width)

# Обработка ширины
@calc_volume.message(CargoCalculator.width)
async def input_width(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение ширины.")
    else:
        await state.update_data(width=int(message.text))
        await message.answer_photo(calculate_volume_photo1, "Введите высоту упаковки (в сантиметрах):")
        await state.set_state(CargoCalculator.height)

# Обработка высоты
@calc_volume.message(CargoCalculator.height)
async def input_height(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение высоты.")
    else:
        await state.update_data(height=int(message.text))
        await message.answer_photo(calculate_volume_photo1, "Теперь введите вес груза (в килограммах):")
        await state.set_state(CargoCalculator.weight)

# Обработка веса и вывод результата
@calc_volume.message(CargoCalculator.weight)
async def input_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        data = await state.get_data()
        volume = data["length"] * data["width"] * data["height"] / 1000000
        density = weight / volume

        await message.answer_photo(calculate_volume_photo5,
            f"Объём груза: {volume:.2f} м³\n"
            f"Плотность груза: {density:.2f} кг/м³", reply_markup=main_keyboard)
        await state.clear()
        await message.answer('Чем я ещё могу вам помочь?', reply_markup=main_inline_keyboard)
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
