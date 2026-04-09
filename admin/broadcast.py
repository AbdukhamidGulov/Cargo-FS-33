from asyncio import sleep
from logging import getLogger

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from database.db_users import get_all_user_tg_ids
from filters_and_config import IsAdmin, admin_ids
from keyboards.admin_keyboards import admin_keyboard, get_broadcast_confirm_keyboard
from keyboards.user_keyboards import cancel_keyboard

admin_broadcast_router = Router()
logger = getLogger(__name__)


class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    confirm_send = State()


@admin_broadcast_router.message(F.text == "Общая рассылка", IsAdmin(admin_ids))
async def start_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📢 <b>Рассылка пользователям</b>\n\n"
        "Отправьте текст сообщения для рассылки.\n"
        "Для отмены напишите: <code>Отмена</code>",
        reply_markup=cancel_keyboard
    )
    await state.set_state(BroadcastStates.waiting_for_text)


@admin_broadcast_router.message(BroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Рассылка отменена.", reply_markup=admin_keyboard)
        return

    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.", reply_markup=cancel_keyboard)
        return

    broadcast_text = message.text.strip()

    if not broadcast_text:
        await message.answer("Сообщение не должно быть пустым.", reply_markup=cancel_keyboard)
        return

    await state.update_data(broadcast_text=broadcast_text)

    preview_text = (
        "📋 <b>Предпросмотр рассылки</b>\n\n"
        f"{broadcast_text}\n\n"
        "<b>Отправить это сообщение всем пользователям?</b>"
    )

    await message.answer(
        preview_text,
        reply_markup=get_broadcast_confirm_keyboard()
    )
    await state.set_state(BroadcastStates.confirm_send)


@admin_broadcast_router.callback_query(BroadcastStates.confirm_send, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer("Рассылка отменена.", reply_markup=admin_keyboard)


@admin_broadcast_router.callback_query(BroadcastStates.confirm_send, F.data == "broadcast_send")
async def execute_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")

    if not broadcast_text:
        await state.clear()
        await callback.message.answer("Текст рассылки не найден. Начните заново.", reply_markup=admin_keyboard)
        return

    user_ids = await get_all_user_tg_ids()

    total = len(user_ids)
    sent_count = 0
    blocked_count = 0
    error_count = 0

    await callback.message.edit_text(
        f"📤 Начинаю рассылку...\nВсего получателей: <b>{total}</b>"
    )

    logger.info(
        "Админ %s запустил рассылку. Получателей: %s",
        callback.from_user.id,
        total
    )

    for tg_id in user_ids:
        try:
            await bot.send_message(chat_id=tg_id, text=broadcast_text)
            sent_count += 1
            await sleep(0.05)

        except TelegramForbiddenError:
            blocked_count += 1
            logger.info("Пользователь %s заблокировал бота. Пропускаю.", tg_id)

        except TelegramRetryAfter as e:
            logger.warning("Flood control при рассылке. Жду %s сек.", e.retry_after)
            await sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=tg_id, text=broadcast_text)
                sent_count += 1
            except TelegramForbiddenError:
                blocked_count += 1
            except Exception as retry_error:
                error_count += 1
                logger.error(
                    "Ошибка повторной отправки пользователю %s: %s",
                    tg_id,
                    retry_error,
                    exc_info=True
                )

        except TelegramBadRequest as e:
            error_count += 1
            logger.warning(
                "TelegramBadRequest при отправке пользователю %s: %s",
                tg_id,
                e
            )

        except Exception as e:
            error_count += 1
            logger.error(
                "Ошибка рассылки пользователю %s: %s",
                tg_id,
                e,
                exc_info=True
            )

    await state.clear()

    report = (
        "✅ <b>Рассылка завершена</b>\n\n"
        f"👥 Всего в базе: <b>{total}</b>\n"
        f"📨 Отправлено: <b>{sent_count}</b>\n"
        f"🚫 Заблокировали бота: <b>{blocked_count}</b>\n"
        f"⚠️ Другие ошибки: <b>{error_count}</b>"
    )

    await callback.message.answer(report, reply_markup=admin_keyboard)

    logger.info(
        "Рассылка завершена. admin=%s total=%s sent=%s blocked=%s errors=%s",
        callback.from_user.id,
        total,
        sent_count,
        blocked_count,
        error_count
    )
