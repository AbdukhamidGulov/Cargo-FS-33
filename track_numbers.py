from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from database import check_or_add_track_code
from keyboards import main_keyboard

track_code = Router()


# Проверка трек-кода
class TrackCode(StatesGroup):
    track_code = State()

@track_code.message(F.text == "Проверка трек-кода")
async def check_track_code(message: Message, state: FSMContext):
    await message.answer("Вставьте ваш скопированный трек-код для проверки:")
    await state.set_state(TrackCode.track_code)

@track_code.message(TrackCode.track_code)
async def process_track_code(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Режим проверки трек-кодов завершён.", reply_markup=main_keyboard)
        await state.clear()
        return

    tg_id = message.from_user.id
    status = await check_or_add_track_code(message.text.strip(), tg_id)
    if status == "in_stock":
        await message.answer("Ваш товар уже на складе.")
    elif status == "out_of_stock":
        await message.answer("Ваш товар ещё не прибыл на склад.")
    else:
        await message.answer("Произошла ошибка. Попробуйте позже.")

    await message.answer("Вы можете отправить следующий трек-код или написать '<code>Отмена</code>' "
                         "для завершения проверки.", reply_markup=ReplyKeyboardRemove())
