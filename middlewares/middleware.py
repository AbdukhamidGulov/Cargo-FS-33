from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
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
            # ПРОВЕРКА НА ОШИБКИ УДАЛЕНИЯ
            # Ошибка AttributeError для InaccessibleMessage
            is_attr_error = isinstance(e, AttributeError) and "InaccessibleMessage" in str(e)
            # Ошибка TelegramBadRequest (сообщение нельзя удалить)
            is_delete_error = isinstance(e, TelegramBadRequest) and "message can't be deleted" in e.message.lower()

            if is_attr_error or is_delete_error:
                # Если это ошибка удаления, мы просто выходим без уведомлений
                return

            # 2. Если произошла другая ошибка, логируем ее полностью
            logger.error(f"Ошибка в хендлере для события {event.__class__.__name__}: {e}", exc_info=True)

            if isinstance(event, (Message, CallbackQuery)):
                # Отправляем уведомление пользователю
                try:
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
                    bot = data.get("bot")

                    if bot:
                        error_message = (
                            f"🚨 **ОШИБКА В БОТЕ** 🚨\n\n"
                            f"**Тип ошибки:** `{type(e).__name__}`\n"
                            f"**Сообщение:** `{e}`"
                        )

                        await bot.send_message(
                            chat_id=ADMIN_TG_ID,
                            text=error_message,
                            parse_mode="Markdown"
                        )

                except Exception as admin_e:
                    logger.error(
                        f"Не удалось отправить уведомление админу ({ADMIN_TG_ID}): {admin_e}",
                        exc_info=False)
            else:
                logger.debug(f"Необработанное событие: {event.__class__.__name__}")

            return
