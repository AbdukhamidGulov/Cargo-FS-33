from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from database import check_or_add_track_code, add_track_codes_list

track_code = Router()


# Проверка трек-кода
class TrackCode(StatesGroup):
    track_code = State()

@track_code.message(F.text == "Проверка трек-кода🔎")
async def check_track_code(message: Message, state: FSMContext):
    await message.answer("Вставьте ваш скопированный трек-код для проверки:")
    await state.set_state(TrackCode.track_code)

@track_code.message(TrackCode.track_code)
async def process_track_code(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    status = await check_or_add_track_code(message.text.strip(), tg_id)
    if status == "in_stock":
        await message.answer("Ваш товар уже на складе.")
    elif status == "out_of_stock":
        await message.answer("Ваш товар ещё не прибыл на склад.")
    else:
        await message.answer("Произошла ошибка. Попробуйте позже.")

    await state.clear()


# Добавление трек-кодов
class TrackCodeStates(StatesGroup):
    waiting_for_track_codes = State()

# Хэндлер для команды /add_track_codes (только для администраторов)
@track_code.callback_query(F.data == "add_track_codes")
async def checking_track_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пожалуйста, отправьте список трек-кодов \n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_track_codes)

@track_code.message(TrackCodeStates.waiting_for_track_codes)
async def process_track_codes(message: Message, state: FSMContext):
    track_codes = list(filter(None, map(str.strip, message.text.split())))
    if not track_codes:
        await message.answer("Список трек-кодов пуст. Пожалуйста, отправьте данные снова.")
        return

    # Добавляем трек-коды в базу данных
    try:
        await add_track_codes_list(track_codes)
        await message.answer(f"Успешно добавлено {len(track_codes)} трек-кодов в базу данных со статусом 'На скаде'.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении трек-кодов: {e}")

    await state.clear()
