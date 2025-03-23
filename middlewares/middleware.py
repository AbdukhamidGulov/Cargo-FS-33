
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
import logging

# Настраиваем логирование
logger = logging.getLogger(__name__)

class ExceptionHandlingMiddleware(BaseMiddleware):
    """Middleware для обработки исключений в хендлерах.
    Перехватывает ошибки, логирует их и отправляет пользователю сообщение."""
    async def __call__(self, handler, event: Update, data: dict):
        """Метод, который вызывается для каждого события."""
        try:
            # Передаём управление хендлеру
            return await handler(event, data)
        except Exception as e:
            # Логируем ошибку
            logger.error(f"Ошибка в хендлере: {e}")
            # Отправляем сообщение пользователю, если это сообщение или callback
            if isinstance(event, (Message, CallbackQuery)):
                await event.answer("Произошла ошибка. Попробуйте позже или обратитесь к администратору.")
            return
