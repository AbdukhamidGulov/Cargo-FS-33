from logging import getLogger

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from admin.admin_search import admin_search_router
from admin.admins_trackcode import admin_tc_router
from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard, confirm_keyboard, contact_admin_keyboard
from database.db_base import setup_database
from database.db_users import drop_users_table
from database.db_track_codes import delete_shipped_track_codes, drop_track_codes_table
from admin.admin_content import admin_content_router

admin_router = Router()
admin_router.include_routers(admin_content_router, admin_search_router, admin_tc_router)
logger = getLogger(__name__)

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


# ------------------------------------------------------------------------------------------


# Обработка функций для удаления с подтверждением
class DangerActions(StatesGroup):
    confirm_action = State()


@admin_tc_router.message(F.text == "Удалить отправленные трек-коды", IsAdmin(admin_ids))
async def initiate_delete_shipped(message: Message, state: FSMContext):
    """Начинает процесс удаления отправленных трек-кодов с запросом подтверждения."""
    await message.delete()
    await ask_confirmation(
        message=message,
        state=state,
        action_type='delete_tracks',
        warning_text="Это удалит ВСЕ отправленные трек-коды!"
    )

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

async def ask_confirmation(message: Message, state: FSMContext, action_type: str, warning_text: str):
    """Запрашивает подтверждение у администратора перед выполнением опасных действий."""
    await state.update_data(action_type=action_type)
    await message.answer(f"⚠️ {warning_text}\n\nВы уверены?", reply_markup=confirm_keyboard)
    await state.set_state(DangerActions.confirm_action)

@admin_router.callback_query(F.data.startswith("danger_"), DangerActions.confirm_action)
async def execute_danger_action(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение или отмену опасных действий, выполняя их при подтверждении."""
    data = await state.get_data()
    action_type = data.get('action_type')

    await callback.message.delete()
    await state.clear()

    if callback.data == "danger_confirm":
        if action_type == 'delete_tracks':
            await delete_shipped_track_codes()
            msg = "Все отправленные трек-коды удалены!"
        elif action_type == 'recreate_users':
            await drop_users_table()
            await setup_database()
            msg = "Таблица пользователей пересоздана!"
        elif action_type == 'recreate_tracks':
            await drop_track_codes_table()
            await setup_database()
            msg = "Таблица трек-кодов пересоздана!"
        await callback.message.answer(f"✅ Успех!\n{msg}")
