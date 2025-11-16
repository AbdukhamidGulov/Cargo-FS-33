from logging import getLogger
from typing import List

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from admin.admin_search import admin_search_router
from admin.admins_trackcode import admin_tc_router
from admin.admin_binding import admin_bulk_router
from database.db_track_admin import delete_shipped_track_codes, bulk_delete_track_codes, drop_track_codes_table
from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard, confirm_keyboard, contact_admin_keyboard, cancel_keyboard
from database.db_base import setup_database
from database.db_users import drop_users_table
from admin.admin_content import admin_content_router
from utils.message_common import extract_text_from_message

admin_router = Router()
admin_router.include_routers(admin_content_router, admin_search_router, admin_tc_router, admin_bulk_router)
logger = getLogger(__name__)

# ************************************************************
# ОСНОВНОЕ МЕНЮ И ПРИВЕТСТВИЯ
# ************************************************************

@admin_router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Открывает панель администратора с выбором команд при нажатии на соответствующую кнопку."""
    await callback.message.answer("Выберите команду", reply_markup=admin_keyboard)
    await callback.answer()

@admin_router.message(Command("admin"), IsAdmin(admin_ids))
@admin_router.message(F.text.lower() == "админ", IsAdmin(admin_ids))
@admin_router.message(Command(commands=['admin_tc_router']), IsAdmin(admin_ids))
async def admin_menu(message: Message):
    """Обрабатывает команду /admin_tc_router для администраторов, показывая меню команд."""
    await message.answer('Выберите команду', reply_markup=admin_keyboard)


@admin_router.message(Command("admin"))
async def admin_contact_command(message: Message):
    """Обрабатывает команду /admin, предлагает связаться с админами через кнопки."""
    await message.answer(
        "Выберите, с каким администратором вы хотели бы связаться:",
        reply_markup=contact_admin_keyboard
    )


# ************************************************************
# ОПАСНЫЕ ДЕЙСТВИЯ С ПОДТВЕРЖДЕНИЕМ (УДАЛЕНИЕ ВСЕХ, ПЕРЕСОЗДАНИЕ)
# ************************************************************

class DangerActions(StatesGroup):
    confirm_action = State()

class DeleteTrackStates(StatesGroup):
    """Состояние для ожидания списка трек-кодов для удаления."""
    waiting_for_codes_to_delete = State()


# ************************************************************
# 1. УДАЛЕНИЕ ВСЕХ ОТПРАВЛЕННЫХ ТРЕК-КОДОВ
# ************************************************************

@admin_tc_router.message(F.text == "Удалить отправленные трек-коды", IsAdmin(admin_ids))
async def initiate_delete_shipped(message: Message, state: FSMContext):
    """Начинает процесс удаления отправленных трек-кодов с запросом подтверждения."""
    await message.delete()
    await ask_confirmation(
        message=message,
        state=state,
        action_type='delete_all_shipped_tracks',
        warning_text="Это удалит ВСЕ отправленные трек-коды!"
    )


# ************************************************************
# 2. УДАЛЕНИЕ ТРЕК-КОДОВ ПО СПИСКУ (с использованием utils/message_common.py)
# ************************************************************

@admin_tc_router.message(F.text == "Удалить трек-коды по списку", IsAdmin(admin_ids))
async def start_list_delete_tracks(message: Message, state: FSMContext):
    """Начинает процесс удаления трек-кодов по списку, ожидая текст или файл."""
    await message.answer(
        "🗑️ <b>Удаление трек-кодов по списку</b>\n\n"
        "Отправьте список трек-кодов:\n"
        "• Можно отправить **текстом** (каждый код с новой строки).\n"
        "• Можно отправить **файлом (.txt)**.\n\n"
        "<i>Пример:</i>\n"
        "<code>YT1234567890123\nYT9876543210987</code>",
        reply_markup=cancel_keyboard,
        parse_mode="HTML"
    )
    await state.set_state(DeleteTrackStates.waiting_for_codes_to_delete)


@admin_tc_router.message(DeleteTrackStates.waiting_for_codes_to_delete)
async def process_list_delete_tracks(message: Message, state: FSMContext):
    """Обрабатывает список трек-кодов из сообщения или файла и запрашивает подтверждение."""
    if message.text and message.text.lower() == "отмена":
        await message.answer("Массовое удаление отменено.", reply_markup=admin_keyboard)
        await state.clear()
        return

    extraction_result = await extract_text_from_message(message)
    track_codes_to_delete: List[str] = extraction_result.get('items', [])
    error_message = extraction_result.get('error')

    if error_message:
        await message.answer(f"❌ Ошибка извлечения данных:\n{error_message}", reply_markup=cancel_keyboard)
        return

    if not track_codes_to_delete:
        await message.answer("❌ Не найдено трек-кодов для удаления. Попробуйте снова.", reply_markup=cancel_keyboard)
        return

    await state.update_data(track_codes_to_delete=track_codes_to_delete)

    warning = (
        f"Вы собираетесь безвозвратно удалить <b>{len(track_codes_to_delete)}</b> трек-кодов из базы данных.\n"
        f"Первые 5 кодов: <code>{', '.join(track_codes_to_delete[:5])}</code>"
    )

    await ask_confirmation(
        message=message,
        state=state,
        action_type='delete_list_tracks',
        warning_text=warning
    )


# ************************************************************
# 3. ПЕРЕСОЗДАНИЕ ТАБЛИЦ
# ************************************************************

@admin_router.message(Command(commands="dp_users"), IsAdmin(admin_ids))
async def initiate_recreate_users(message: Message, state: FSMContext):
    """Начинает процесс пересоздания таблицы пользователей с запросом подтверждения."""
    await ask_confirmation(
        message=message,
        state=state,
        action_type='recreate_users',
        warning_text="Это ПОЛНОСТЬЮ удалит таблицу пользователей и создаст её заново!"
    )

@admin_router.message(Command(commands="dp_tracks"), IsAdmin(admin_ids))
async def initiate_recreate_tracks(message: Message, state: FSMContext):
    """Начинает процесс пересоздания таблицы трек-кодов с запросом подтверждения."""
    await ask_confirmation(
        message=message,
        state=state,
        action_type='recreate_tracks',
        warning_text="Это ПОЛНОСТЬЮ удалит таблицу трек-кодов и создаст её заново!"
    )

# ************************************************************
# ОБЩИЕ ФУНКЦИИ
# ************************************************************

async def ask_confirmation(message: Message, state: FSMContext, action_type: str, warning_text: str):
    """Запрашивает подтверждение у администратора перед выполнением опасных действий."""
    await state.update_data(action_type=action_type)
    await message.answer(f"⚠️ {warning_text}\n\nВы уверены?", reply_markup=confirm_keyboard, parse_mode="HTML")
    await state.set_state(DangerActions.confirm_action)

@admin_router.callback_query(F.data.startswith("danger_"), DangerActions.confirm_action)
async def execute_danger_action(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение или отмену опасных действий, выполняя их при подтверждении."""
    data = await state.get_data()
    action_type = data.get('action_type')
    track_codes_to_delete: List[str] = data.get('track_codes_to_delete', [])

    await callback.message.delete()
    await state.clear()

    if callback.data == "danger_confirm":
        msg = "Неизвестное действие."

        if action_type == 'delete_all_shipped_tracks':
            await delete_shipped_track_codes()
            msg = "Все отправленные трек-коды удалены!"

        elif action_type == 'delete_list_tracks':
            if track_codes_to_delete:
                success_count, failed_count = await bulk_delete_track_codes(track_codes_to_delete)
                msg = (
                    f"Массовое удаление завершено.\n"
                    f"✅ Успешно удалено: <b>{success_count}</b>\n"
                    f"❌ Ошибки удаления: <b>{failed_count}</b>"
                )
            else:
                msg = "Ошибка: не найден список трек-кодов для удаления в состоянии FSM."

        elif action_type == 'recreate_users':
            await drop_users_table()
            await setup_database()
            msg = "Таблица пользователей пересоздана!"

        elif action_type == 'recreate_tracks':
            await drop_track_codes_table()
            await setup_database()
            msg = "Таблица трек-кодов пересоздана!"

        await callback.message.answer(f"✅ Успех!\n{msg}", parse_mode="HTML")
    else:
        await callback.message.answer("❌ Действие отменено.", reply_markup=admin_keyboard)