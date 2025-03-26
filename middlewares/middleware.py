from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
import logging

from filters_and_config import admin_ids

logger = logging.getLogger(__name__)

class ExceptionHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка в хендлере для события {event.__class__.__name__}: {e}", exc_info=True)
            if isinstance(event, (Message, CallbackQuery)):
                await event.answer("Произошла ошибка. Попробуйте позже или обратитесь к администратору.")
                if admin_ids:
                    await data["bot"].send_message(admin_ids[0], f"Ошибка: {e}\nUser: {event.from_user.id}")
            else:
                logger.debug(f"Необработанное событие: {event.__class__.__name__}")
            return
