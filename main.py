from os import getenv
from asyncio import run
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from get_information import gi
from registration_process import states
from keyboards import main_keyboard, reg_keyboard
from database import create_users_table, get_user_by_tg_id

load_dotenv()
TELEGRAM_BOT_TOKEN = getenv('BOT_TOKEN')

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(gi, states)


@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer('Вас приветствует Telegram-бот карго компании <b>FS-33</b> 🚚')
    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer('Я помогу вам найти адреса складов, проверить трек-код и ознакомить с ценами',
                             reply_markup=main_keyboard)
    else:
        await message.answer('Вы ещё не зарегистрированы чтобы пользоватся нашим ботом\n\n'
                             'Хотите зарегистрироваться?', reply_markup=reg_keyboard)


@dp.message(Command(commands=['help']))
async def help_command(message: Message):
    await message.answer('Команда хелп')


@dp.message(Command(commands=["create_db"]))
async def create_db_command(message: Message):
    await create_users_table()
    await message.answer("База данных пользователей успешно создана!")


async def main():
    try:
        print("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        print("Сессия бота закрыта")

if __name__ == "__main__":
    run(main())


# @dp.message(F.photo)
# async def photo(message: Message):
#     await message.answer(message.photo[0].file_id)
