from logging import getLogger

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from admin.admins_trackcode import admin_tc_router
from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard, confirm_keyboard, contact_admin_keyboard, main_keyboard, cancel_keyboard, \
    get_admin_edit_user_keyboard
from database.base import setup_database
from database.users import get_user_by_id, drop_users_table, update_user_by_internal_id
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


class AdminEditUserStates(StatesGroup):
    waiting_for_new_username = State()
    waiting_for_new_phone = State()
    user_id_to_edit = State()


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
    username = user_data.get('username')
    phone = user_data.get('phone')

    # Создаем инфо-сообщение
    await message.answer(
        f"ID: <code>FS{user_data['id']:04d}</code>\n"
        f"Имя: {user_data.get('name') or no_value}\n"
        f"Username: @{username or no_value}\n"
        f"Номер телефона: {phone or no_value}\n\n",
        # reply_markup=cancel_keyboard # <-- Убираем старую клавиатуру
    )

    # Создаем новую инлайн-клавиатуру для редактирования
    edit_keyboard = get_admin_edit_user_keyboard(
        internal_user_id=user_data['id'],
        has_username=bool(username),
        has_phone=bool(phone)
    )

    # Отправляем отдельное сообщение с кнопками редактирования и инструкцией
    await message.answer(
        "Вы можете изменить данные этого пользователя, нажав кнопки ниже, "
        "ввести следующий ID для поиска или нажать '<code>Отмена</code>'.",
        reply_markup=edit_keyboard
    )
    # НЕ очищаем состояние SearchUserStates.waiting_for_user_id,
    # чтобы админ мог сразу искать следующий ID
    logger.info(f"Админ {message.from_user.id} получил информацию о пользователе с ID {user_id}.")


# ------------------------------------------------------------------------------------------
# --- НОВЫЕ ХЕНДЛЕРЫ ДЛЯ РЕДАКТИРОВАНИЯ ---
# ------------------------------------------------------------------------------------------

# --- Редактирование НИКНЕЙМА ---

@admin_router.callback_query(F.data.startswith("admin_edit_username:"))
async def start_edit_username(callback: CallbackQuery, state: FSMContext):
    """Начинает FSM для изменения никнейма пользователя."""
    try:
        user_id_to_edit = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: неверный ID пользователя.", show_alert=True)
        return

    # Очищаем старое состояние (поиска) и устанавливаем новое (редактирования)
    await state.clear()
    await state.set_state(AdminEditUserStates.waiting_for_new_username)
    await state.update_data(user_id_to_edit=user_id_to_edit)

    await callback.message.answer(
        f"Вы редактируете пользователя <code>FS{user_id_to_edit:04d}</code>.\n"
        "Отправьте новый никнейм (без @) или '<code>-</code>' (дефис) для удаления никнейма.",
        reply_markup=cancel_keyboard
    )
    await callback.answer()


@admin_router.message(AdminEditUserStates.waiting_for_new_username, F.text)
async def process_edit_username(message: Message, state: FSMContext):
    """Сохраняет новый никнейм."""
    if message.text == "Отмена":
        await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    data = await state.get_data()
    user_id_to_edit = data.get('user_id_to_edit')

    new_username = message.text.strip().replace("@", "")  # Очищаем от @

    if new_username == "-":
        new_username = None  # Устанавливаем None для удаления

    success = await update_user_by_internal_id(user_id_to_edit, username=new_username)

    if success:
        await message.answer(f"✅ Никнейм для <code>FS{user_id_to_edit:04d}</code> успешно обновлен.",
                             reply_markup=main_keyboard)
    else:
        await message.answer("❌ Произошла ошибка при обновлении никнейма.", reply_markup=main_keyboard)

    await state.clear()


# --- Редактирование ТЕЛЕФОНА ---

@admin_router.callback_query(F.data.startswith("admin_edit_phone:"))
async def start_edit_phone(callback: CallbackQuery, state: FSMContext):
    """Начинает FSM для изменения телефона пользователя."""
    try:
        user_id_to_edit = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: неверный ID пользователя.", show_alert=True)
        return

    # Очищаем старое состояние (поиска) и устанавливаем новое (редактирования)
    await state.clear()
    await state.set_state(AdminEditUserStates.waiting_for_new_phone)
    await state.update_data(user_id_to_edit=user_id_to_edit)

    await callback.message.answer(
        f"Вы редактируете пользователя <code>FS{user_id_to_edit:04d}</code>.\n"
        "Отправьте новый номер телефона или '<code>-</code>' (дефис) для удаления номера.",
        reply_markup=cancel_keyboard
    )
    await callback.answer()


@admin_router.message(AdminEditUserStates.waiting_for_new_phone, F.text)
async def process_edit_phone(message: Message, state: FSMContext):
    """Сохраняет новый телефон."""
    if message.text == "Отмена":
        await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    data = await state.get_data()
    user_id_to_edit = data.get('user_id_to_edit')

    new_phone = message.text.strip()

    if new_phone == "-":
        new_phone = None  # Устанавливаем None для удаления

    success = await update_user_by_internal_id(user_id_to_edit, phone=new_phone)

    if success:
        await message.answer(f"✅ Телефон для <code>FS{user_id_to_edit:04d}</code> успешно обновлен.",
                             reply_markup=main_keyboard)
    else:
        await message.answer("❌ Произошла ошибка при обновлении телефона.", reply_markup=main_keyboard)

    await state.clear()


# --- Обработка "Отмены" для новых состояний ---
@admin_router.message(AdminEditUserStates.waiting_for_new_username, F.text == "Отмена")
@admin_router.message(AdminEditUserStates.waiting_for_new_phone, F.text == "Отмена")
async def cancel_admin_edit(message: Message, state: FSMContext):
    await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
    await state.clear()
