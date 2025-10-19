from logging import getLogger

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from admin.admins_trackcode import admin_tc_router
from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard, confirm_keyboard, contact_admin_keyboard, main_keyboard, cancel_keyboard
from database.base import setup_database
from database.users import get_user_by_id, drop_users_table
from database.track_codes import delete_shipped_track_codes, drop_track_codes_table
from admin.admin_content import admin_content_router

admin_router = Router()
admin_router.include_routers(admin_content_router, admin_tc_router)
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


# Искать информацию по ID
class SearchUserStates(StatesGroup):
    waiting_for_user_id = State()

@admin_router.message(F.text == "Искать инфо по ID")
async def start_user_search(message: Message, state: FSMContext):
    """Начинает процесс поиска информации о пользователе по ID, запрашивая ввод ID."""
    await message.answer("Введите ID пользователя (например, FS0001 или просто 1):")
    await state.set_state(SearchUserStates.waiting_for_user_id)
    logger.info(f"Админ {message.from_user.id} начал поиск пользователя по ID.")

@admin_router.message(SearchUserStates.waiting_for_user_id)
async def process_user_search_input(message: Message, state: FSMContext):
    """Обрабатывает введенный ID пользователя, возвращая его данные или сообщение об ошибке."""
    if message.text == "Отмена":
        await message.answer("Поиск пользователя по ID завершен.", reply_markup=main_keyboard)
        await state.clear()
        logger.info(f"Админ {message.from_user.id} завершил поиск пользователя по ID.")
        return

    user_id_str = message.text.strip()  # Удаляем лишние пробелы для точности

    if user_id_str.startswith("FS"):  # Проверяем и преобразуем ID в зависимости от формата
        numeric_part = user_id_str[2:]  # Если ID начинается с "FS", извлекаем числовую часть
        if numeric_part.isdigit():
            user_id = int(numeric_part)
        else:
            await message.answer("Пожалуйста, введите корректный ID пользователя в формате FSXXXX, где XXXX — число.",
        reply_markup=cancel_keyboard)
            return

    elif user_id_str.isdigit():
        user_id = int(user_id_str)  # Если ID — это просто число

    else:
        await message.answer("Пожалуйста, введите числовой ID пользователя или в формате FSXXXX."
                             "\nИли напишите <code>Отмена</code> чтобы остановить режим поиска по  ID",
        reply_markup=cancel_keyboard)  # Если формат неверный
        return

    user_data = await get_user_by_id(user_id)  # Получаем данные пользователя

    if not user_data:
        await message.answer("Пользователь с таким ID не найден.")
        return

    # Формируем ответ с данными пользователя
    no_value = "<i>Не заполнено</i>"
    await message.answer(
        f"ID: <code>FS{user_data['id']:04d}</code>\n"
        f"Имя: {user_data['name'] or no_value}\n"
        f"Username: @{user_data['username'] or no_value}\n"
        f"Номер телефона: {user_data['phone'] or no_value}\n\n"
        f"<i>Напишите новый ID для поиска или нажмите <code>Отмена</code>, чтобы выйти из режима поиска</i>",
        reply_markup=cancel_keyboard
    )

    await message.answer(
        "Вы можете ввести следующий ID пользователя для поиска или нажать '<code>Отмена</code>', чтобы завершить.",
        reply_markup=cancel_keyboard
    )
    logger.info(f"Админ {message.from_user.id} получил информацию о пользователе с ID {user_id}.")


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
