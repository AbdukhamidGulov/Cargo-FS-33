from sys import stdout
from asyncio import run
from logging import basicConfig, getLogger, WARNING

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.admin.admin_panel import admin_router
from bot.commands import commands_router
from bot.profile import profile_router
from request import request_router
from database.base import setup_database
from track_numbers import track_code_router
from get_information import get_info_router
from registration_process import states_router
from calculator.calc_volume import calc_volume_router
from calculator.calculate_insurance import calc_ins_router
from calculator.calculate_shipping import calc_shipping_router
from middlewares.middleware import ExceptionHandlingMiddleware
from filters_and_config import TELEGRAM_BOT_TOKEN

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(commands_router, admin_router, get_info_router, states_router, profile_router,
                   track_code_router, request_router, calc_volume_router, calc_ins_router, calc_shipping_router)
dp.update.outer_middleware(ExceptionHandlingMiddleware())

basicConfig(level=WARNING, stream=stdout)
logger = getLogger(__name__)


async def main():
    """Основная функция для запуска Telegram-бота с использованием long polling."""
    await setup_database()
    logger.info('База данных инициализирована')
    # await set_default_commands(bot)

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    run(main())