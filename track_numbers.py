from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from database import check_or_add_track_code

track_numbers = Router()


class TrackCode(StatesGroup):
    track_code = State()

@track_numbers.callback_query(F.data == "checking_track_code")
async def checking_track_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Вставьте ваш скопированный трек-код для проверки:")
    await state.set_state(TrackCode.track_code)

@track_numbers.message(TrackCode.track_code)
async def process_track_code(message: Message, state: FSMContext):
    track_code = message.text.strip()
    tg_id = message.from_user.id
    status = await check_or_add_track_code(track_code, tg_id)
    if status == "in_stock":
        await message.answer("Ваш товар уже на складе.")
    elif status == "out_of_stock":
        await message.answer("Ваш товар ещё не прибыл на склад.")
    else:
        await message.answer("Произошла ошибка. Попробуйте позже.")

    await state.clear()
