from os import getenv
from asyncio import run
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

from filters import IsAdmin
from change_processor import change
from track_numbers import track_code
from get_information import get_info
from registration_process import states
from calculator.calc_handlers import calc
from calculator.calc_volume import calc_volume
from calculator.calculate_shipping import calc_shipping
from keyboards import main_keyboard, reg_keyboard, admin_keyboard
from database import create_users_table, get_user_by_tg_id, drop_users_table, create_track_numbers_table, \
    drop_track_numbers_table

load_dotenv()
TELEGRAM_BOT_TOKEN = getenv('BOT_TOKEN')
admin_ids: list[int] = [5302111687]

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(get_info, change, states, track_code, calc, calc_volume, calc_shipping)


@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer_photo(
        'AgACAgIAAxkBAAIElGdLMwTg5ryGW34KC5nWUmfQEjlgAAL65TEb4nBYSpjvLhbFuxviAQADAgADcwADNgQ',
        'Вас приветствует Telegram-бот карго компании <b>FS-33</b> 🚚')
    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer('Я помогу вам найти адреса складов, проверить трек-код и ознакомить с ценами',
                             reply_markup=main_keyboard)
    else:
        await message.answer('Вы ещё не зарегистрированы чтобы пользоватся нашим ботом\n\n'
                             'Хотите зарегистрироваться?', reply_markup=reg_keyboard)


@dp.message(Command(commands=['admin']), IsAdmin(admin_ids))
async def admin_command(message: Message):
    await message.answer('  <u>Список доступных команд:</u>\n', reply_markup=admin_keyboard)


@dp.message(Command(commands=['admin']))
async def admin_command(message: Message):
    await message.answer('Вы не явяетесь админом')
    await bot.send_message(admin_ids[0], text=f"Пользоватеь {message.from_user.username} "
                                              f"c id {message.from_user.id} нажал на команду <b>admin</b>")
    print("message.from_user.id")


@dp.message(Command(commands=['help']))
async def help_command(message: Message):
    await message.answer('Команда хелп')


@dp.callback_query(F.data == "add_track_codes")
async def checking_track_code(callback: CallbackQuery):
    await drop_users_table()
    await create_users_table()
    await callback.message.answer('База данных пользователей успешно песоздана!')


@dp.callback_query(F.data == "add_track_codes")
async def checking_track_code(callback: CallbackQuery):
    await drop_track_numbers_table()
    await create_track_numbers_table()
    await callback.message.answer('База данных Трек-номеров успешно песоздана!')


@dp.message(F.photo)
async def photo(message: Message):
    await message.answer(print_token_photo := message.photo[0].file_id)
    print(print_token_photo)


async def main():
    try:
        await create_users_table()
        await create_track_numbers_table()
        print('Бот запущен')
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        print('Сессия бота закрыта')

if __name__ == "__main__":
    run(main())
