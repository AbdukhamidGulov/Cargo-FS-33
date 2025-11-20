from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from database.db_track_codes import get_track_code
from database.db_users import get_info_profile, get_user_by_id, update_user_by_internal_id
from keyboards import get_admin_edit_user_keyboard, cancel_keyboard, main_keyboard
from filters_and_config import IsAdmin, admin_ids

admin_search_router = Router()
logger = getLogger(__name__)


class AdminSearchAndEditStates(StatesGroup):
    waiting_for_owner_search_code = State()
    waiting_for_user_id = State()
    waiting_for_new_username = State()
    waiting_for_new_phone = State()


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def _display_user_info(message: Message, user_data: dict, prefix: str = ""):
    """Выводит карточку пользователя с кнопками редактирования."""
    tg_id = user_data.get('tg_id')
    internal_id = user_data.get('id')
    name = user_data.get('name') or "Не указано"
    username = user_data.get('username')
    phone = user_data.get('phone')

    info_text = (
        f"ID: <code>FS{internal_id:04d}</code>\n"
        f"Имя: {name}\n"
        f"Username: @{username or 'Не указано'}\n"
        f"Телефон: {phone or 'Не указано'}\n"
        f"TG ID: <code>{tg_id}</code>\n"
        f"<a href='tg://user?id={tg_id}'>Написать пользователю</a>"
    )

    if prefix:
        info_text = f"{prefix}\n\n{info_text}"

    await message.answer(info_text)

    await message.answer(
        "Выберите действие или введите данные для нового поиска:",
        reply_markup=get_admin_edit_user_keyboard(
            internal_user_id=internal_id,
            has_username=bool(username),
            has_phone=bool(phone)
        )
    )


# ************************************************
# 1. ПОИСК ВЛАДЕЛЬЦА ПО ТРЕК-КОДУ
# ************************************************

@admin_search_router.message(F.text == "Найти владельца трек-кода", IsAdmin(admin_ids))
async def find_owner_start(message: Message, state: FSMContext):
    await message.answer("Отправьте трек-код для поиска владельца.", reply_markup=cancel_keyboard)
    await state.set_state(AdminSearchAndEditStates.waiting_for_owner_search_code)


@admin_search_router.message(AdminSearchAndEditStates.waiting_for_owner_search_code)
async def process_owner_search(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Поиск отменен.", reply_markup=main_keyboard)
        await state.clear()
        return

    track_code = message.text.strip()
    info = await get_track_code(track_code)

    if not info:
        await message.answer(
            f"❌ Трек-код <code>{track_code}</code> не найден в базе.",
            reply_markup=cancel_keyboard
        )
        return

    # Код найден, проверяем владельца
    owner_tg_id = info.get('tg_id')
    status = info.get('status', 'неизвестен')

    if not owner_tg_id:
        await message.answer(
            f"⚠️ <b>Код найден, но не привязан:</b>\n"
            f"Код: <code>{track_code}</code>\n"
            f"Статус: <b>{status}</b>\n"
            f"Владелец: ❌ Не установлен",
            reply_markup=cancel_keyboard
        )
        return

    # Владелец есть, ищем его профиль
    user_data = await get_info_profile(owner_tg_id)

    if user_data:
        prefix = f"✅ <b>Владелец найден (Статус кода: {status})</b>"
        await _display_user_info(message, user_data, prefix)
    else:
        # Ситуация, когда tg_id есть в таблице треков, но нет в таблице юзеров (редкий баг)
        await message.answer(
            f"⚠️ <b>Ошибка целостности данных:</b>\n"
            f"Код: {track_code}\n"
            f"Привязан к TG ID: <code>{owner_tg_id}</code>\n"
            f"❌ Но профиль этого пользователя не найден в базе.",
            reply_markup=cancel_keyboard
        )


# ************************************************
# 2. ПОИСК ПОЛЬЗОВАТЕЛЯ ПО ID (FS...)
# ************************************************

@admin_search_router.message(F.text == "Искать инфо по ID", IsAdmin(admin_ids))
async def start_user_search(message: Message, state: FSMContext):
    await message.answer("Введите ID (например: <b>FS1234</b> или <b>1234</b>):", reply_markup=cancel_keyboard)
    await state.set_state(AdminSearchAndEditStates.waiting_for_user_id)


@admin_search_router.message(AdminSearchAndEditStates.waiting_for_user_id)
async def process_user_search_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if text.lower() == "отмена":
        await message.answer("Поиск отменен.", reply_markup=main_keyboard)
        await state.clear()
        return

    # Очистка ввода (FS1234 -> 1234)
    clean_id = text.upper().replace("FS", "")

    if not clean_id.isdigit():
        await message.answer("❌ Неверный формат. Введите число или FSxxxx.", reply_markup=cancel_keyboard)
        return

    user_id = int(clean_id)
    user_data = await get_user_by_id(user_id)

    if not user_data:
        await message.answer(f"❌ Пользователь FS{user_id:04d} не найден.", reply_markup=cancel_keyboard)
        return

    await _display_user_info(message, user_data, prefix="✅ <b>Пользователь найден:</b>")


# ************************************************
# 3. РЕДАКТИРОВАНИЕ ПОЛЬЗОВАТЕЛЯ
# ************************************************

@admin_search_router.callback_query(F.data.startswith("admin_edit_"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext):
    """Единый обработчик для начала редактирования (username или phone)."""
    action, user_id_str = callback.data.replace("admin_edit_", "").split(":")
    user_id = int(user_id_str)

    await state.update_data(user_id_to_edit=user_id)

    msg_text = f"Редактирование <code>FS{user_id:04d}</code>.\n"

    if action == "username":
        msg_text += "Отправьте новый <b>Username</b> (без @) или '-':"
        await state.set_state(AdminSearchAndEditStates.waiting_for_new_username)
    elif action == "phone":
        msg_text += "Отправьте новый <b>Телефон</b> или '-':"
        await state.set_state(AdminSearchAndEditStates.waiting_for_new_phone)

    await callback.message.answer(msg_text, reply_markup=cancel_keyboard)
    await callback.answer()


@admin_search_router.message(AdminSearchAndEditStates.waiting_for_new_username)
@admin_search_router.message(AdminSearchAndEditStates.waiting_for_new_phone)
async def process_edit_save(message: Message, state: FSMContext):
    """Единый обработчик сохранения (username или phone)."""
    if message.text.lower() == "отмена":
        await message.answer("Отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    data = await state.get_data()
    user_id = data.get('user_id_to_edit')
    current_state = await state.get_state()

    value = message.text.strip()
    if value == "-": value = None

    success = False
    field_name = ""

    if current_state == AdminSearchAndEditStates.waiting_for_new_username:
        if value: value = value.replace("@", "")
        success = await update_user_by_internal_id(user_id, username=value)
        field_name = "Никнейм"

    elif current_state == AdminSearchAndEditStates.waiting_for_new_phone:
        success = await update_user_by_internal_id(user_id, phone=value)
        field_name = "Телефон"

    if success:
        await message.answer(f"✅ {field_name} для FS{user_id:04d} обновлен.", reply_markup=main_keyboard)
    else:
        await message.answer("❌ Ошибка обновления БД.", reply_markup=main_keyboard)

    await state.clear()
