from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from typing import Any, Awaitable, Callable, Dict
import logging

from filters_and_config import admin_ids

logger = logging.getLogger(__name__)

# Индекс админа, которому отправляем уведомления (согласно твоему запросу)
ADMIN_INDEX_FOR_ALERTS = 1


class ExceptionHandlingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        try:
            # 1. Попытка выполнить основной хендлер
            return await handler(event, data)

        except Exception as e:
            # 2. Если произошла ошибка, логируем ее полностью
            logger.error(f"Ошибка в хендлере для события {event.__class__.__name__}: {e}", exc_info=True)

            if isinstance(event, (Message, CallbackQuery)):
                # Отправляем уведомление пользователю
                await event.answer(
                    "Произошла ошибка. Попробуйте позже или обратитесь к техническому администратору @abdulhamidgulov")

                # --- БЛОК НАДЕЖНОЙ ОТПРАВКИ СООБЩЕНИЯ АДМИНУ ---
                try:
                    bot = data.get("bot")  # Получаем объект бота

                    # Проверяем, что бот существует и есть нужный админ в списке
                    if bot and admin_ids and len(admin_ids) > ADMIN_INDEX_FOR_ALERTS:
                        admin_id = admin_ids[ADMIN_INDEX_FOR_ALERTS]
                        user_id = event.from_user.id
                        username = event.from_user.username

                        # Формируем сообщение об ошибке
                        error_message = (
                            f"🚨 **КРИТИЧЕСКАЯ ОШИБКА В БОТЕ** 🚨\n\n"
                            f"**Событие:** `{event.__class__.__name__}`\n"
                            f"**Ошибка:** `{type(e).__name__}`\n"
                            f"**Сообщение:** `{e}`\n"
                            f"**Пользователь:**\n"
                            f"  - ID: `{user_id}`\n"
                            f"  - Ник: `@{username}`"
                        )

                        # Отправляем сообщение админу с форматированием Markdown
                        await bot.send_message(
                            chat_id=admin_id,
                            text=error_message,
                            parse_mode="Markdown"
                        )

                except Exception as admin_e:
                    # Логгируем ошибку, если не удалось отправить сообщение админу
                    # (например, бот заблокирован админом)
                    logger.error(
                        f"Не удалось отправить уведомление админу ({admin_ids[ADMIN_INDEX_FOR_ALERTS]}): {admin_e}",
                        exc_info=False)
                # ----------------------------------------------------

            else:
                logger.debug(f"Необработанное событие: {event.__class__.__name__}")

            # Важно: После обработки ошибки мы возвращаемся из __call__, не пропуская событие дальше
            return
