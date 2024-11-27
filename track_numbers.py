from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from database import get_track_codes_list

track_numbers = Router()


class TrackCode(StatesGroup):
    track_code = State()


@track_numbers.callback_query(F.data == "checking_track_code")
async def checking_track_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Вставте ваш скопированный трек код для проверки")
    await state.set_state(TrackCode.track_code)

@track_numbers.message(TrackCode.track_code)
async def add_user_name(message: Message, state: FSMContext):
    track_code = message.text
    track_codes_list = await get_track_codes_list()
    if track_code in track_codes_list:
        pass
    await state.clear()
