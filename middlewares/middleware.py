from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from typing import Any, Awaitable, Callable, Dict
from logging import getLogger

logger = getLogger(__name__)

ADMIN_TG_ID = 8058104515


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
                try:
                    # Для CallbackQuery используем answer, для Message - answer
                    if isinstance(event, CallbackQuery):
                        await event.answer(
                            "Произошла ошибка. Попробуйте позже, нажмите /start или обратитесь к техническому администратору @abdulhamidgulov")
                    else:
                        await event.answer(
                            "Произошла ошибка. Попробуйте позже, нажмите /start или обратитесь к техническому администратору @abdulhamidgulov")
                except Exception:
                    # Игнорируем ошибки, если не смогли ответить пользователю
                    pass

                # --- БЛОК НАДЕЖНОЙ ОТПРАВКИ СООБЩЕНИЯ АДМИНУ ---
                try:
                    bot = data.get("bot")  # Получаем объект бота

                    # Проверяем, что объект бота существует
                    if bot:
                        error_message = (
                            f"🚨 **ОШИБКА В БОТЕ** 🚨\n\n"
                            f"**Тип ошибки:** `{type(e).__name__}`\n"
                            f"**Сообщение:** `{e}`"
                        )

                        # Отправляем сообщение на жестко заданный ID
                        await bot.send_message(
                            chat_id=ADMIN_TG_ID,
                            text=error_message,
                            parse_mode="Markdown"
                        )

                except Exception as admin_e:
                    # Логгируем ошибку, если не удалось отправить сообщение админу
                    logger.error(
                        f"Не удалось отправить уведомление админу ({ADMIN_TG_ID}): {admin_e}",
                        exc_info=False)
                # ----------------------------------------------------

            else:
                logger.debug(f"Необработанное событие: {event.__class__.__name__}")

            # Важно: После обработки ошибки мы возвращаемся из __call__, не пропуская событие дальше
            return
