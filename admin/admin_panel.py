from logging import getLogger
from typing import List

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from admin.admin_search import admin_search_router
from admin.admins_trackcode import admin_tc_router
from admin.admin_binding import admin_bulk_router
from admin.admin_content import admin_content_router
from admin.broadcast import admin_broadcast_router
from database.db_track_codes import drop_track_codes_table, delete_multiple_track_codes
from database.db_track_admin import delete_shipped_track_codes
from database.db_base import setup_database
from database.db_users import drop_users_table
from filters_and_config import IsAdmin, admin_ids
from keyboards.admin_keyboards import admin_keyboard, contact_admin_keyboard, confirm_keyboard
from keyboards.user_keyboards import cancel_keyboard
from utils.message_common import extract_text_from_message

admin_router = Router()
admin_router.include_routers(
    admin_content_router,
    admin_search_router,
    admin_tc_router,
    admin_bulk_router,
    admin_broadcast_router
)
logger = getLogger(__name__)


class DangerActions(StatesGroup):
    confirm_action = State()


class DeleteTrackStates(StatesGroup):
    waiting_for_codes_to_delete = State()


@admin_router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    await callback.message.answer("Выберите команду", reply_markup=admin_keyboard)
    await callback.answer()


@admin_router.message(Command("admin"), IsAdmin(admin_ids))
@admin_router.message(F.text.lower() == "админ", IsAdmin(admin_ids))
@admin_router.message(Command(commands=["admin_tc_router"]), IsAdmin(admin_ids))
async def admin_menu(message: Message):
    await message.answer("Выберите команду", reply_markup=admin_keyboard)


@admin_router.message(Command("admin"))
async def admin_contact_command(message: Message):
    await message.answer(
        "Выберите, с каким администратором вы хотели бы связаться:",
        reply_markup=contact_admin_keyboard
    )


@admin_router.message(F.text == "Удалить отправленные трек-коды", IsAdmin(admin_ids))
async def initiate_delete_shipped(message: Message, state: FSMContext):
    try:
        await message.delete()
    except Exception:
        pass

    await ask_confirmation(
        message,
        state,
        action_type="delete_all_shipped_tracks",
        warning_text="Это удалит ВСЕ отправленные трек-коды!"
    )


@admin_router.message(F.text == "Удалить трек-коды по списку", IsAdmin(admin_ids))
async def start_list_delete_tracks(message: Message, state: FSMContext):
    await message.answer(
        "🗑️ <b>Удаление по списку</b>\n\n"
        "Отправьте список кодов (текст или файл).",
        reply_markup=cancel_keyboard
    )
    await state.set_state(DeleteTrackStates.waiting_for_codes_to_delete)


@admin_router.message(DeleteTrackStates.waiting_for_codes_to_delete)
async def process_list_delete_tracks(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() == "отмена":
        await message.answer("Массовое удаление отменено.", reply_markup=admin_keyboard)
        await state.clear()
        return

    content = await extract_text_from_message(message, bot)

    if not content:
        if not message.document:
            await message.answer("❌ Ошибка: отправьте текст или файл.", reply_markup=cancel_keyboard)
        return

    track_codes_to_delete = [line.strip() for line in content.splitlines() if line.strip()]

    if not track_codes_to_delete:
        await message.answer("❌ Не найдено трек-кодов для удаления.", reply_markup=cancel_keyboard)
        return

    await state.update_data(track_codes_to_delete=track_codes_to_delete)

    preview = ", ".join(track_codes_to_delete[:5])
    warning = (
        f"Вы собираетесь безвозвратно удалить <b>{len(track_codes_to_delete)}</b> кодов.\n"
        f"Первые 5: <code>{preview}</code>"
    )

    await ask_confirmation(
        message,
        state,
        action_type="delete_list_tracks",
        warning_text=warning
    )


@admin_router.message(Command(commands="dp_users"), IsAdmin(admin_ids))
async def initiate_recreate_users(message: Message, state: FSMContext):
    await ask_confirmation(
        message,
        state,
        action_type="recreate_users",
        warning_text="Это ПОЛНОСТЬЮ удалит таблицу пользователей и создаст её заново!"
    )


@admin_router.message(Command(commands="dp_tracks"), IsAdmin(admin_ids))
async def initiate_recreate_tracks(message: Message, state: FSMContext):
    await ask_confirmation(
        message,
        state,
        action_type="recreate_tracks",
        warning_text="Это ПОЛНОСТЬЮ удалит таблицу трек-кодов и создаст её заново!"
    )


async def ask_confirmation(message: Message, state: FSMContext, action_type: str, warning_text: str):
    await state.update_data(action_type=action_type)
    await message.answer(f"⚠️ {warning_text}\n\nВы уверены?", reply_markup=confirm_keyboard)
    await state.set_state(DangerActions.confirm_action)


@admin_router.callback_query(F.data.startswith("danger_"), DangerActions.confirm_action)
async def execute_danger_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    action_type = data.get("action_type")
    track_codes_to_delete: List[str] = data.get("track_codes_to_delete", [])

    await callback.message.delete()
    await state.clear()

    if callback.data == "danger_confirm":
        msg = "Неизвестное действие."

        if action_type == "delete_all_shipped_tracks":
            deleted_count = await delete_shipped_track_codes()
            msg = f"Удалено {deleted_count} отправленных трек-кодов!"

        elif action_type == "delete_list_tracks":
            if track_codes_to_delete:
                deleted_count = await delete_multiple_track_codes(track_codes_to_delete)
                failed_count = len(track_codes_to_delete) - deleted_count

                msg = (
                    f"Массовое удаление завершено.\n"
                    f"✅ Успешно удалено: <b>{deleted_count}</b>\n"
                    f"❌ Не найдено в БД: <b>{failed_count}</b>"
                )
            else:
                msg = "Ошибка: не найден список трек-кодов для удаления."

        elif action_type == "recreate_users":
            await drop_users_table()
            await setup_database()
            msg = "Таблица пользователей пересоздана!"

        elif action_type == "recreate_tracks":
            await drop_track_codes_table()
            await setup_database()
            msg = "Таблица трек-кодов пересоздана!"

        await callback.message.answer(f"✅ Успех!\n{msg}")
    else:
        await callback.message.answer("❌ Действие отменено.", reply_markup=admin_keyboard)
