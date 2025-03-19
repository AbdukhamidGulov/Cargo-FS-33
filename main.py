from asyncio import run
from sys import stdout
from logging import basicConfig, getLogger, INFO

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties

from request import request
from admin_panel import admin
from change_processor import change
from track_numbers import track_code
from get_information import get_info
from text_info import main_menu_photo
from registration_process import states
from database.base import setup_database
from database.users import get_user_by_tg_id
from calculator.calc_volume import calc_volume
from calculator.calculate_insurance import calc_ins
from calculator.calculate_shipping import calc_shipping
from keyboards import main_keyboard, reg_keyboard, get_main_inline_keyboard
from filters_and_config import TELEGRAM_BOT_TOKEN

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(admin, get_info, change, states, track_code, request, calc_volume, calc_ins, calc_shipping)
basicConfig(level=INFO, stream=stdout)
logger = getLogger(__name__)


@dp.message(CommandStart())
@dp.message(F.text == "Вернуться в главное меню")
async def start_command(message: Message):
    """
    Обрабатывает команду `/start` и сообщение "Вернуться в главное меню".

    Отправляет приветственное фото и текст, проверяет, зарегистрирован ли пользователь в базе данных.
    Если пользователь зарегистрирован, отправляет основное меню; если нет — предлагает регистрацию.

    Args:
        message (Message): Объект сообщения от пользователя, содержащий информацию о чате и отправителе.

    Raises:
        Exception: Если произошла ошибка при обращении к базе данных (например, она недоступна).
    """
    await message.answer_photo(
        main_menu_photo,
        'Вас приветствует Telegram-бот карго компании <b>FS-33</b> 🚚'
    )

    try:
        user = await get_user_by_tg_id(message.from_user.id)
        if user:
            await message.answer(
                'Я помогу вам найти адреса складов, проверить трек-код и ознакомить с ценами',
                reply_markup=main_keyboard
            )
            await message.answer(
                'Как я могу вам помочь?',
                reply_markup=get_main_inline_keyboard(message.from_user.id)
            )
        else:
            await message.answer(
                'Вы ещё не зарегистрированы чтобы пользоваться нашим ботом\n\n'
                'Хотите зарегистрироваться?',
                reply_markup=reg_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке регистрации пользователя {message.from_user.id}: {e}")
        await message.answer(
            "Произошла ошибка при проверке вашей регистрации. Попробуйте позже или обратитесь к администратору."
        )


async def main():
    """
    Основная функция для запуска Telegram-бота.

    Инициализирует таблицы в базе данных, запускает polling для обработки сообщений и корректно завершает сессию бота.

    Raises:
        Exception: Если произошла ошибка при создании таблиц или запуске polling (например, проблемы с подключением).
    """
    try:
        await setup_database()
        logger.info('База данных инициализирована')
        await dp.start_polling(bot)
        logger.info('Бот начал polling')
    except Exception as e:
        logger.exception(f'Произошла ошибка при запуске бота: {e}')
    finally:
        await bot.session.close()
        logger.info('Сессия бота закрыта')


if __name__ == "__main__":
    run(main())
