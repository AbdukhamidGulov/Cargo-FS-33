from sys import stdout
from asyncio import run
from logging import basicConfig, getLogger, WARNING, INFO

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from text_info import text
from request import request_router
from profile import profile_router
from commands import commands_router
from database.db_base import setup_database
from admin.admin_panel import admin_router
from track_numbers import track_code_router
from get_information import get_info_router
from registration_process import states_router
from order_maker.create_order import order_router
from order_maker.user_collector import user_data_router
from calculator.calc_volume import calc_volume_router
from track_codes_search import track_code_search_router
from calculator.calculate_insurance import calc_ins_router
from calculator.calculate_shipping import calc_shipping_router
from middlewares.middleware import ExceptionHandlingMiddleware
from filters_and_config import TELEGRAM_BOT_TOKEN

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(commands_router, admin_router, get_info_router, states_router, profile_router, text,
                   track_code_router, track_code_search_router, user_data_router, order_router, request_router,
                   calc_volume_router, calc_ins_router, calc_shipping_router)
dp.update.outer_middleware(ExceptionHandlingMiddleware())

basicConfig(level=WARNING, stream=stdout)
logger = getLogger(__name__)


async def main():
    """Основная функция для запуска Telegram-бота с использованием long polling."""
    await setup_database()
    logger.info('База данных инициализирована')
    print("Бот запущен")

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    run(main())

# ✅ Добавил новых админов
# ✅ Добавил массовое добавление трек кодов
# ✅ Добавил новые кнопки после добавления трек кодов
# ✅ Добавил массовою проверку трек кодов
# ✅ В админ панели добавил функцию удаление одного или множество трек-кодов
# ✅ В админ панели добавил функцию поиска владельца трек-кода - с трек-кодом
# ✅ Изменил Консолидацию переписав функцию и другие текста по-просьбе девчат
# ✅ Сделал новую вкладку для Бланка таможни с кучей доработок и написание новой функции
# ✅ Переписал функцию "Изменит данные" для админов, создав категории и русские имена
# ✅ Добавил заполнение никнейма - админами
# ✅ Изменил функцию найти по ID добавив "Ссылка на чат: Написать пользователю"
# ✅ Добавил проверку большего количества трек кодов - файлом
# ✅ Плюс добавил проверку трек кодов - файлом
# ✅ Добавил для админов функцию привязки трек-кодов пользователям
# ✅ изменил кнопки
# ✅ Добавил функцию создание ексел таблици + админами
# Не работает функция привязки трек кодов админами
# добавить в новую функцию поддержку через временные файли. Чтобы заполняемые данные хранились в бд пока таблица не создаться


# В будущем нужно добавить возможность добавить имя трек-коду, даты поступления на склад, отправки из склада и поступлению в пункт выдачи
