from logging import Logger
from typing import Dict, Tuple

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from keyboards.user_keyboards import (
    main_keyboard,
    get_order_keyboard,
    order_cancel_confirm_keyboard,
)


def _build_restore_prompt(previous_state: str | None, items_count: int, state_ids: Dict[str, str]) -> Tuple[str, object]:
    if previous_state == state_ids["waiting_for_photo"]:
        return (
            "Продолжаем заполнение.\n\n"
            f"📦 <b>Товар №{items_count + 1}</b>\n"
            "📸 <b>Отправьте фото товара</b>:\n\n"
            "Для отмены напишите: <code>/cancel</code>",
            ReplyKeyboardRemove(),
        )

    if previous_state == state_ids["waiting_for_quantity"]:
        return (
            "Продолжаем заполнение.\n\n"
            "🔢 <b>Введите количество</b>:",
            ReplyKeyboardRemove(),
        )

    if previous_state == state_ids["waiting_for_track_code"]:
        return (
            "Продолжаем заполнение.\n\n"
            "🚚 <b>Введите трек-номер</b>:",
            ReplyKeyboardRemove(),
        )

    if previous_state == state_ids["waiting_for_link"]:
        return (
            "Продолжаем заполнение.\n\n"
            "🔗 <b>Ссылка на товар</b> или описание:",
            ReplyKeyboardRemove(),
        )

    if previous_state == state_ids["confirm_next_step"]:
        return (
            "Продолжаем заполнение.\n\n"
            "Что дальше?",
            get_order_keyboard(),
        )

    return (
        "Продолжаем заполнение.\n\n"
        "Введите следующее значение.",
        ReplyKeyboardRemove(),
    )


async def ask_order_cancel_confirmation(
    message: Message,
    state: FSMContext,
    confirm_state,
    logger: Logger,
) -> None:
    data = await state.get_data()
    items_count = len(data.get("items", []))
    previous_state = await state.get_state()

    await state.update_data(previous_state=previous_state)

    logger.info(
        "Запрошено подтверждение отмены заполнения бланка. tg_id=%s items_count=%s previous_state=%s",
        message.from_user.id,
        items_count,
        previous_state,
    )

    await message.answer(
        "⚠️ Вы уверены, что хотите отменить заполнение бланка?\n\n"
        f"Уже сохранено товаров: <b>{items_count}</b>\n"
        "Если подтвердить, введённые данные будут потеряны.",
        reply_markup=order_cancel_confirm_keyboard,
    )
    await state.set_state(confirm_state)


async def confirm_order_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    logger: Logger,
) -> None:
    try:
        await callback.answer()
    except Exception:
        pass

    logger.info(
        "Пользователь подтвердил отмену заполнения бланка. tg_id=%s",
        callback.from_user.id,
    )

    if isinstance(callback.message, Message):
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning("Не удалось удалить сообщение подтверждения отмены: %s", e)

        await callback.message.answer(
            "Заполнение бланка отменено. Все несохранённые данные сброшены.",
            reply_markup=main_keyboard,
        )

    await state.clear()


async def continue_order_after_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    logger: Logger,
    state_ids: Dict[str, str],
) -> None:
    try:
        await callback.answer()
    except Exception:
        pass

    data = await state.get_data()
    previous_state = data.get("previous_state")
    items_count = len(data.get("items", []))

    logger.info(
        "Пользователь отказался от отмены и продолжает заполнение. tg_id=%s previous_state=%s items_count=%s",
        callback.from_user.id,
        previous_state,
        items_count,
    )

    text, reply_markup = _build_restore_prompt(previous_state, items_count, state_ids)

    if isinstance(callback.message, Message):
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning("Не удалось удалить сообщение подтверждения отмены: %s", e)

        await callback.message.answer(text, reply_markup=reply_markup)

    if previous_state:
        await state.set_state(previous_state)
