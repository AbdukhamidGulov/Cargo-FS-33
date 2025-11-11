from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup

from database.db_info_content import get_info_content
from keyboards import main_keyboard, get_main_inline_keyboard

calc_volume_router = Router()

class CargoCalculator(StatesGroup):
    length = State()  # длина
    width = State()   # ширина
    height = State()  # высота
    weight = State()  # вес


@calc_volume_router.message(F.text == "Калькулятор объёма")
async def calculate_volume(message: Message, state: FSMContext):
    """Начинает процесс расчёта объёма груза."""
    await message.delete()
    photo_id = await get_info_content("calculate_volume_photo")
    if photo_id:
        await message.answer_photo(
            photo_id,
            "❗️<i>Что такое плотность и для чего она нужна? "
            "<a href='https://t.me/cargoFS33/1426'>Читайте здесь</a></i>\n\n"
            "Для расчёта плотности груза введите длину груза (в сантиметрах):"
        )
        await state.update_data(photo_id=photo_id)
        await state.set_state(CargoCalculator.length)
    else:
        await message.answer("Фото для расчёта объёма не найдено. Обратитесь к администратору.")
        await state.clear()


# Обработка длины
@calc_volume_router.message(CargoCalculator.length)
async def input_length(message: Message, state: FSMContext):
    """Обрабатывает ввод длины груза."""
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение длины.")
    else:
        await state.update_data(length=int(message.text))
        data = await state.get_data()
        photo_id = data.get("photo_id")
        if photo_id:
            await message.answer_photo(photo_id, "Введите ширину упаковки (в сантиметрах):")
            await state.set_state(CargoCalculator.width)
        else:
            await message.answer("Фото не найдено. Начните заново.")
            await state.clear()


# Обработка ширины
@calc_volume_router.message(CargoCalculator.width)
async def input_width(message: Message, state: FSMContext):
    """Обрабатывает ввод ширины груза."""
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение ширины.")
    else:
        await state.update_data(width=int(message.text))
        data = await state.get_data()
        photo_id = data.get("photo_id")
        if photo_id:
            await message.answer_photo(photo_id, "Введите высоту упаковки (в сантиметрах):")
            await state.set_state(CargoCalculator.height)
        else:
            await message.answer("Фото не найдено. Начните заново.")
            await state.clear()


# Обработка высоты
@calc_volume_router.message(CargoCalculator.height)
async def input_height(message: Message, state: FSMContext):
    """Обрабатывает ввод высоты груза."""
    if not message.text.isdigit():
        await message.answer("Введите целое числовое значение высоты.")
    else:
        await state.update_data(height=int(message.text))
        data = await state.get_data()
        photo_id = data.get("photo_id")
        if photo_id:
            await message.answer_photo(photo_id, "Теперь введите вес груза (в килограммах):")
            await state.set_state(CargoCalculator.weight)
        else:
            await message.answer("Фото не найдено. Начните заново.")
            await state.clear()


# Обработка веса и вывод результата
@calc_volume_router.message(CargoCalculator.weight)
async def input_weight(message: Message, state: FSMContext):
    """Обрабатывает ввод веса и выводит результат расчёта."""
    try:
        weight = float(message.text)
        data = await state.get_data()
        volume = data["length"] * data["width"] * data["height"] / 1000000
        density = weight / volume
        result_photo = await get_info_content("calculate_volume_photo_end")
        if result_photo:
            await message.answer_photo(
                result_photo,
                f"Объём груза: {volume:.2f} м³\n"
                f"Плотность груза: {density:.2f} кг/м³",
                reply_markup=main_keyboard
            )
            await message.answer('Чем я ещё могу вам помочь?', reply_markup=get_main_inline_keyboard(message.from_user.id))
        else:
            await message.answer("Фото результата не найдено.")
        await state.clear()
    except ValueError:
        await message.answer("Введите числовое значение веса.")