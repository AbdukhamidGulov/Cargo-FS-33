from asyncio import run
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties

from admin_panel import admin
from change_processor import change
from track_numbers import track_code
from get_information import get_info
from registration_process import states
from calculator.calc_handlers import calc
from calculator.calc_volume import calc_volume
from calculator.calculate_shipping import calc_shipping
from keyboards import main_keyboard, reg_keyboard, main_inline_keyboard
from filters_and_config import TELEGRAM_BOT_TOKEN
from database import create_users_table, get_user_by_tg_id, create_track_codes_table

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(admin,  get_info, change, states, track_code, calc, calc_volume, calc_shipping)


@dp.message(CommandStart())
@dp.message(F.text == "Вернуться в главное меню")
async def start_command(message: Message):
    await message.answer_photo(
        'AgACAgIAAxkBAAIElGdLMwTg5ryGW34KC5nWUmfQEjlgAAL65TEb4nBYSpjvLhbFuxviAQADAgADcwADNgQ',
        'Вас приветствует Telegram-бот карго компании <b>FS-33</b> 🚚')
    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer('Я помогу вам найти адреса складов, проверить трек-код и ознакомить с ценами',
                             reply_markup=main_keyboard)
    else:
        await message.answer('Вы ещё не зарегистрированы чтобы пользоваться нашим ботом\n\n'
                             'Хотите зарегистрироваться?', reply_markup=reg_keyboard)


async def main():
    try:
        await create_users_table()
        await create_track_codes_table()
        print('Бот запущен')
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        print('Сессия бота закрыта')

if __name__ == "__main__":
    run(main())

