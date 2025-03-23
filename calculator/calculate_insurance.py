from aiohttp import ClientSession
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from keyboards import main_keyboard, item_type_keyboard,  get_main_inline_keyboard

calc_ins_router = Router()
item_types = [
    "Объёмный груз",
    "Одежда",
    "Ткань",
    "Ноутбуки",
    "Телефоны",
    "Продукты",
    "Электроника",
    "Аптека"
]

class InsuranceState(StatesGroup):
    cost = State()  # Ввод стоимости
    weight = State()  # Ввод веса
    item_type = State()  # Выбор типа товара

# Старт расчёта страховки
@calc_ins_router.message(F.text == "Рассчитать страховку")
async def start_insurance(message: Message, state: FSMContext):
    await message.delete()
    await message.answer("Введите стоимость груза в юанях:")
    await state.set_state(InsuranceState.cost)

# Ввод стоимости
@calc_ins_router.message(InsuranceState.cost)
async def enter_cost(message: Message, state: FSMContext):
    try:
        cost = float(message.text.replace("¥", "").strip())
        await state.update_data(cost=cost)
        await message.answer("Введите вес груза в кг:")
        await state.set_state(InsuranceState.weight)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение стоимости.")

# Ввод веса
@calc_ins_router.message(InsuranceState.weight)
async def enter_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.strip())
        await state.update_data(weight=weight)
        await message.answer("Выберите тип товара:", reply_markup=item_type_keyboard)
        await state.set_state(InsuranceState.item_type)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение веса.")

# Выбор типа товара
@calc_ins_router.message(InsuranceState.item_type)
async def enter_item_type(message: Message, state: FSMContext):
    if message.text not in item_types:
        await message.answer("Пожалуйста, выберите один из предложенных типов товара.")
        return

    data = await state.get_data()
    cost_cny = data["cost"]
    weight = data["weight"]
    item_type = message.text

    # Получение курса валют

    async with ClientSession() as session:
        async with session.get("https://api.exchangerate-api.com/v4/latest/USD") as response:
            rates = await response.json()
            usd_to_rub = rates["rates"]["RUB"]
            cny_to_usd = rates["rates"]["USD"] / rates["rates"]["CNY"]

    # Перевод стоимости
    cost_usd = cost_cny * cny_to_usd
    price_per_kg = cost_usd / weight

    # Определение процента страховки
    if price_per_kg <= 20:
        insurance_rate = 1.5
    elif 20 < price_per_kg <= 30:
        insurance_rate = 2.5
    elif 30 < price_per_kg <= 40:
        insurance_rate = 3.5
    else:
        await message.answer("Стоимость 1 кг превышает допустимые лимиты.")
        return

    # Расчёт страховки
    insurance_cost_usd = cost_usd * (insurance_rate / 100)
    insurance_cost_rub = insurance_cost_usd * usd_to_rub

    # Вывод результата
    await message.answer(
        f"💴 Стоимость заказа в юанях: {cost_cny}¥\n"
        f"💲 Стоимость заказа в долларах: {cost_usd:.2f}$\n\n"
        f"🔹 Род товара: {item_type}\n"
        f"🔹 Вес: {weight:.2f} кг.\n\n"
        f"🔸 Стоимость 1 кг. товара: {price_per_kg:.2f}$\n"
        f"🔸 Страховка при стоимости {price_per_kg:.2f}$ за 1 кг. "
        f"составит: {insurance_rate}%\n\n"
        f"ИТОГО:\n"
        f"💲 Сумма страховки в долларах: {insurance_cost_usd:.2f}$\n"
        f"🇷🇺 Сумма страховки в руб.: {insurance_cost_rub:.0f} руб." ,
        reply_markup=main_keyboard
    )
    await state.clear()
    await message.answer('Чем я ещё могу вам помочь?', reply_markup=get_main_inline_keyboard(message.from_user.id))
