from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from database.track_codes import get_track_code_info
from database.users import get_info_profile, get_user_by_id, update_user_by_internal_id
from keyboards import (
    get_admin_edit_user_keyboard,
    cancel_keyboard,
    main_keyboard
)
from filters_and_config import IsAdmin, admin_ids

admin_search_router = Router()
logger = getLogger(__name__)


class TrackCodeStates(StatesGroup):
    # Состояния для добавления/удаления
    waiting_for_codes = State()
    waiting_for_arrived_codes = State()
    waiting_for_codes_to_delete = State()

    # Состояния для поиска/редактирования
    waiting_for_owner_search_code = State()
    waiting_for_user_id = State()
    waiting_for_new_username = State()
    waiting_for_new_phone = State()


# ************************************************
# ОБЩАЯ ФУНКЦИЯ ОТОБРАЖЕНИЯ ИНФО О ПОЛЬЗОВАТЕЛЕ
# ************************************************

async def _display_user_info_with_controls(message: Message, user_data: dict, prefix_message: str = ""):
    """
    Вспомогательная функция для отображения данных пользователя и кнопок редактирования.
    """
    no_value = "<i>Не заполнено</i>"
    username = user_data.get('username')
    phone = user_data.get('phone')
    user_tg_id = user_data.get('tg_id')
    internal_user_id = user_data.get('id')

    # 1. Отправляем основную информацию
    response = (
        f"ID: <code>FS{internal_user_id:04d}</code>\n"
        f"Имя: {user_data['name'] or no_value}\n"
        f"Username: @{username or no_value}\n"
        f"Номер телефона: {phone or no_value}\n"
        f"Telegram ID: <code>{user_tg_id}</code>\n"
        f"Ссылка на чат: <a href='tg://user?id={user_tg_id}'>Написать пользователю</a>"
    )

    if prefix_message:
        response = prefix_message + "\n\n" + response

    await message.answer(response)

    # 2. Генерируем клавиатуру редактирования
    edit_keyboard = get_admin_edit_user_keyboard(
        internal_user_id=internal_user_id,
        has_username=bool(username),
        has_phone=bool(phone)
    )

    # 3. Отправляем второе сообщение с кнопками
    await message.answer(
        "Вы можете <b>изменить данные</b> этого пользователя, "
        "ввести следующий ID/трек-код для поиска или нажать '<b>Отмена</b>'.",
        reply_markup=edit_keyboard
    )


# ************************************************
# ПОИСК ВЛАДЕЛЬЦА (по Трек-коду)
# ************************************************

@admin_search_router.message(F.text == "Найти владельца трек-кода", IsAdmin(admin_ids))
async def find_owner_start(message: Message, state: FSMContext):
    """Начинает процесс поиска владельца по трек-коду."""
    await message.answer("Пожалуйста, отправьте трек-код для поиска владельца.",
                         reply_markup=cancel_keyboard)
    await state.set_state(TrackCodeStates.waiting_for_owner_search_code)


@admin_search_router.message(TrackCodeStates.waiting_for_owner_search_code, F.text == "Отмена")
async def cancel_owner_search(message: Message, state: FSMContext):
    """Отменяет режим поиска владельца."""
    await message.answer("Поиск владельца отменен.", reply_markup=main_keyboard)
    await state.clear()


@admin_search_router.message(TrackCodeStates.waiting_for_owner_search_code)
async def process_owner_search(message: Message, state: FSMContext):
    """Ищет владельца и статус по введенному трек-коду."""
    if not message.text or message.text.lower() == "отмена":
        await message.answer("Пожалуйста, введите корректный трек-код.", reply_markup=cancel_keyboard)
        return

    track_code = message.text.strip()
    track_info = await get_track_code_info(track_code)

    if track_info:
        user_tg_id = track_info.get('tg_id')
        status = track_info.get('status', 'неизвестен')

        if user_tg_id:
            user_data = await get_info_profile(user_tg_id)
            if user_data:
                prefix = (
                    f"✅ <b>Найден владелец для <code>{track_code}</code> (Статус: {status})</b>"
                )
                await _display_user_info_with_controls(message, user_data, prefix_message=prefix)
            else:
                await message.answer(
                    f"⚠️ <b>Информация о трек-коде:</b>\n"
                    f"Код: <code>{track_code}</code> (Статус: <b>{status}</b>)\n"
                    f"Владелец (TG ID): <code>{user_tg_id}</code>\n"
                    f"<b>Ошибка:</b> Не удалось найти профиль пользователя с этим TG ID в базе `users`.",
                    reply_markup=cancel_keyboard
                )
        else:
            await message.answer(
                f"⚠️ <b>Информация о трек-коде:</b>\n"
                f"Код: <code>{track_code}</code> (Статус: <b>{status}</b>)\n"
                f"Владелец: <b>Не привязан к пользователю.</b>\n\n"
                f"Вы можете ввести следующий трек-код или нажать 'Отмена'.",
                reply_markup=cancel_keyboard
            )
    else:
        await message.answer(f"❌ Трек-код <code>{track_code}</code> не найден в базе данных.",
                             reply_markup=cancel_keyboard)

    # Остаемся в состоянии


# ************************************************
# ПОИСК ПОЛЬЗОВАТЕЛЯ (по ID)
# ************************************************

@admin_search_router.message(F.text == "Искать инфо по ID", IsAdmin(admin_ids))
async def start_user_search(message: Message, state: FSMContext):
    """Начинает процесс поиска информации о пользователе по ID, запрашивая ввод ID."""
    await message.answer("Введите ID пользователя (например, FS0001 или просто 1):",
                         reply_markup=cancel_keyboard)
    await state.set_state(TrackCodeStates.waiting_for_user_id)
    logger.info(f"Админ {message.from_user.id} начал поиск пользователя по ID.")


@admin_search_router.message(TrackCodeStates.waiting_for_user_id, F.text == "Отмена")
async def cancel_user_search(message: Message, state: FSMContext):
    """Отменяет режим поиска пользователя по ID."""
    await message.answer("Поиск пользователя по ID отменен.", reply_markup=main_keyboard)
    await state.clear()


@admin_search_router.message(TrackCodeStates.waiting_for_user_id)
async def process_user_search_input(message: Message, state: FSMContext):
    """Обрабатывает введенный ID пользователя, возвращая его данные или сообщение об ошибке."""

    user_id_str = message.text.strip()
    user_id = None

    if user_id_str.startswith("FS"):
        numeric_part = user_id_str[2:]
        if numeric_part.isdigit():
            user_id = int(numeric_part)
        else:
            await message.answer("Пожалуйста, введите корректный ID пользователя в формате FSXXXX, где XXXX — число.",
                                 reply_markup=cancel_keyboard)
            return

    elif user_id_str.isdigit():
        user_id = int(user_id_str)

    else:
        await message.answer("Пожалуйста, введите числовой ID пользователя или в формате FSXXXX."
                             "\nИли напишите <code>Отмена</code> чтобы остановить режим поиска по ID",
                             reply_markup=cancel_keyboard)
        return

    user_data = await get_user_by_id(user_id)

    if not user_data:
        await message.answer("Пользователь с таким ID не найден.", reply_markup=cancel_keyboard)
        return

    await _display_user_info_with_controls(message, user_data, prefix_message=f"✅ <b>Найден пользователь по ID:</b>")

    logger.info(f"Админ {message.from_user.id} получил информацию о пользователе с ID {user_id}.")
    # Остаемся в состоянии


# ************************************************************
# ОБРАБОТЧИКИ КНОПОК РЕДАКТИРОВАНИЯ
# ************************************************************

@admin_search_router.callback_query(F.data.startswith("admin_edit_username:"))
async def start_edit_username(callback: CallbackQuery, state: FSMContext):
    """Начинает FSM для изменения никнейма пользователя."""
    try:
        user_id_to_edit = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: неверный ID пользователя.", show_alert=True)
        return

    await state.clear()
    await state.set_state(TrackCodeStates.waiting_for_new_username)
    await state.update_data(user_id_to_edit=user_id_to_edit)

    await callback.message.answer(
        f"Вы редактируете пользователя <code>FS{user_id_to_edit:04d}</code>.\n"
        "Отправьте новый никнейм (без @) или '<code>-</code>' (дефис) для удаления никнейма.",
        reply_markup=cancel_keyboard
    )
    await callback.answer()


@admin_search_router.message(TrackCodeStates.waiting_for_new_username, F.text == "Отмена")
async def cancel_edit_username(message: Message, state: FSMContext):
    """Отменяет редактирование никнейма."""
    await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
    await state.clear()


@admin_search_router.message(TrackCodeStates.waiting_for_new_username)
async def process_edit_username(message: Message, state: FSMContext):
    """Сохраняет новый никнейм."""
    if message.text.lower() == "отмена":
        await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    data = await state.get_data()
    user_id_to_edit = data.get('user_id_to_edit')

    new_username = message.text.strip().replace("@", "")

    if new_username == "-":
        new_username = None

    success = await update_user_by_internal_id(user_id_to_edit, username=new_username)

    if success:
        await message.answer(f"✅ Никнейм для <code>FS{user_id_to_edit:04d}</code> успешно обновлен.",
                             reply_markup=main_keyboard)
    else:
        await message.answer("❌ Произошла ошибка при обновлении никнейма.", reply_markup=main_keyboard)

    await state.clear()


@admin_search_router.callback_query(F.data.startswith("admin_edit_phone:"))
async def start_edit_phone(callback: CallbackQuery, state: FSMContext):
    """Начинает FSM для изменения телефона пользователя."""
    try:
        user_id_to_edit = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: неверный ID пользователя.", show_alert=True)
        return

    await state.clear()
    await state.set_state(TrackCodeStates.waiting_for_new_phone)
    await state.update_data(user_id_to_edit=user_id_to_edit)

    await callback.message.answer(
        f"Вы редактируете пользователя <code>FS{user_id_to_edit:04d}</code>.\n"
        "Отправьте новый номер телефона или '<code>-</code>' (дефис) для удаления номера.",
        reply_markup=cancel_keyboard
    )
    await callback.answer()


@admin_search_router.message(TrackCodeStates.waiting_for_new_phone, F.text == "Отмена")
async def cancel_edit_phone(message: Message, state: FSMContext):
    """Отменяет редактирование телефона."""
    await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
    await state.clear()


@admin_search_router.message(TrackCodeStates.waiting_for_new_phone)
async def process_edit_phone(message: Message, state: FSMContext):
    """Сохраняет новый телефон."""
    if message.text.lower() == "отмена":
        await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    data = await state.get_data()
    user_id_to_edit = data.get('user_id_to_edit')

    new_phone = message.text.strip()

    if new_phone == "-":
        new_phone = None

    success = await update_user_by_internal_id(user_id_to_edit, phone=new_phone)

    if success:
        await message.answer(f"✅ Телефон для <code>FS{user_id_to_edit:04d}</code> успешно обновлен.",
                             reply_markup=main_keyboard)
    else:
        await message.answer("❌ Произошла ошибка при обновлении телефона.", reply_markup=main_keyboard)

    await state.clear()
