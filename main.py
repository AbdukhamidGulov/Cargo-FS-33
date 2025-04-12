from sys import stdout
from asyncio import run, sleep
from logging import basicConfig, getLogger, WARNING

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from text_info import text
from request import request_router
from profile import profile_router
from database.base import setup_database
from admin.admin_panel import admin_router
from track_numbers import track_code_router
from get_information import get_info_router
from database.users import get_user_by_tg_id
from registration_process import states_router
from database.info_content import get_info_content
from calculator.calc_volume import calc_volume_router
from calculator.calculate_insurance import calc_ins_router
from calculator.calculate_shipping import calc_shipping_router
from keyboards import main_keyboard, reg_keyboard, get_main_inline_keyboard
from middlewares.middleware import ExceptionHandlingMiddleware
from filters_and_config import TELEGRAM_BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
dp.include_routers(admin_router, get_info_router, states_router, profile_router, text,
                   track_code_router, request_router, calc_volume_router, calc_ins_router, calc_shipping_router)
dp.update.outer_middleware(ExceptionHandlingMiddleware())
WEBHOOK_URL = f'https://{WEBHOOK_HOST}{WEBHOOK_PATH}'
basicConfig(level=WARNING, stream=stdout)
logger = getLogger(__name__)

photo_cache = {}  # Кэш для хранения главного фото
async def get_cached_content(key: str) -> str:
    """Получает значение из кэша или базы данных, если его нет в кэше."""
    if key not in photo_cache:
        photo_cache[key] = await get_info_content(key)
    return photo_cache[key]

@dp.message(CommandStart())
@dp.message(F.text == "Вернуться в главное меню")
async def start_command(message: Message):
    """Обрабатывает команду `/start` и сообщение "Вернуться в главное меню".

    Отправляет приветственное фото и текст, проверяет, зарегистрирован ли пользователь в базе данных.
    Если пользователь зарегистрирован, отправляет основное меню; если нет — предлагает регистрацию."""
    main_menu_photo = await get_cached_content("main_menu_photo")
    await message.answer_photo(
        main_menu_photo,
        'Вас приветствует Telegram-бот карго компании <b>FS-33</b> 🚚'
    )
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
            'Вы ещё не зарегистрированы, чтобы пользоваться нашим ботом\n\n'
            'Хотите зарегистрироваться?',
            reply_markup=reg_keyboard
        )



async def on_startup(app):
    """Действия при старте бота (установка вебхука)."""
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        try:
            await bot.set_webhook(url=WEBHOOK_URL)
            logger.info(f"Вебхук установлен на: {WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Не удалось установить вебхук: {e}")

async def on_shutdown():
    """Действия при завершении работы бота (удаление вебхука)."""
    try:
        await bot.delete_webhook()
        logger.info("Вебхук удален.")
    except Exception as e:
        logger.error(f"Не удалось удалить вебхук: {e}")
    finally:
        await bot.session.close()
        logger.info('Сессия бота закрыта')


async def main():
    """Основная функция для запуска Telegram-бота с использованием webhook."""
    await setup_database()
    logger.info('База данных инициализирована')

    app = web.Application()
    # Создать экземпляр WebhookRequestHandler с диспетчером и ботом
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    # Зарегистрировать обработчик вебхука по пути
    webhook_handler.register(app, path=WEBHOOK_PATH)

    # Вызвать действия при старте (установить вебхук)
    app.on_startup.append(on_startup)
    # Вызвать действия при завершении работы (удалить вебхук)
    app.on_shutdown.append(on_shutdown)

    # Настроить приложение и запустить веб-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()
    logger.info(f"Веб-сервер запущен на http://{WEBAPP_HOST}:{WEBAPP_PORT}{WEBHOOK_PATH}")

    # Поддерживать работу сервера до ручной остановки
    while True:
        await sleep(3600)  # Спать один час


if __name__ == "__main__":
    run(main())
