from logging import getLogger
from typing import Dict, Any

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from database.db_users import get_info_profile, update_user_info, get_user_by_id
from keyboards.user_keyboards import cancel_keyboard, main_keyboard
from filters_and_config import admin_ids

user_data_router = Router()
logger = getLogger(__name__)


class UserDataStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_tg_link = State()
    waiting_for_email = State()
    admin_waiting_for_client_code = State()


# --- УТИЛИТЫ ---

def format_client_info(user_info: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Формирует сводку данных клиента."""
    name = data.get('client_name') or user_info.get('name') or '❌ Не заполнено'

    # Определяем контакт
    username = user_info.get('username')
    phone = user_info.get('phone')
    tg_contact = f"@{username}" if username else (phone or '❌ Не заполнено')
    tg_contact = data.get('client_tg', tg_contact)

    return (
        f"📝 <b>Данные для бланка:</b>\n\n"
        f"<b>Код клиента:</b> {data.get('client_excel_id', 'N/A')}\n"
        f"<b>Имя:</b> {name}\n"
        f"<b>Контакт:</b> {tg_contact}\n"
        f"<b>Email:</b> {data.get('client_email', '❓ Будет запрошен')}"
    )


async def cancel_data_collection(message: Message, state: FSMContext):
    await message.answer("Создание бланка отменено.", reply_markup=main_keyboard)
    await state.clear()


async def check_missing_data_and_prompt(message: Message, state: FSMContext, user_info: dict, is_admin: bool = False):
    """Умная проверка: ищет, чего не хватает, и запрашивает это. Иначе — запрашивает Email."""
    prefix = "✍️ <b>Данные клиента:</b>\n" if is_admin else "📦 <b>Данные для заказа:</b>\n"

    # 1. Имя
    if not user_info.get('name'):
        await message.answer(f"{prefix}Введите <b>Имя</b> клиента:", reply_markup=cancel_keyboard)
        await state.set_state(UserDataStates.waiting_for_name)
        return

    await state.update_data(client_name=user_info['name'])

    # 2. Контакт (Username или Телефон)
    if not user_info.get('username') and not user_info.get('phone'):
        await message.answer(f"{prefix}Введите ссылку на <b>Telegram</b> (@username) или номер телефона:",
                             reply_markup=cancel_keyboard)
        await state.set_state(UserDataStates.waiting_for_tg_link)
        return

    contact = f"@{user_info['username']}" if user_info.get('username') else user_info.get('phone')
    await state.update_data(client_tg=contact)

    # 3. Email (всегда спрашиваем последним)
    await message.answer("📧 Введите <b>Email</b> (или '-' чтобы пропустить):", reply_markup=cancel_keyboard)
    await state.set_state(UserDataStates.waiting_for_email)


# --- ТОЧКА ВХОДА ---
@user_data_router.message(F.text == "Бланк для Таможни")
async def start_order_process(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()

    # Режим Админа
    if user_id in admin_ids:
        await message.answer(
            "💻 <b>Режим админа для заполнения Бланка Таможни</b>\nВведите ID клиента (число или FSxxxx):",
            reply_markup=cancel_keyboard
        )
        await state.set_state(UserDataStates.admin_waiting_for_client_code)
        return

    # Режим Пользователя
    user_info = await get_info_profile(user_id)
    if not user_info:
        await message.answer("❌ Ошибка профиля. Нажмите /start")
        return

    await state.update_data(
        items=[],
        client_id=user_id,
        client_excel_id=f"FS{user_info['id']:04d}",
        form_title="Таможенный Бланк"
    )

    await message.answer("📝 Начинаем заполнение...")
    await check_missing_data_and_prompt(message, state, user_info)


# --- ОБРАБОТКА ДАННЫХ ---

@user_data_router.message(UserDataStates.admin_waiting_for_client_code)
async def admin_process_client_code(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_data_collection(message, state)

    text = message.text.strip().upper().replace("FS", "")
    if not text.isdigit():
        await message.answer("❌ Введите корректный ID (например, 1234).")
        return

    internal_id = int(text)
    client_info = await get_user_by_id(internal_id)

    if not client_info or not client_info.get('tg_id'):
        await message.answer(f"❌ Клиент FS{internal_id:04d} не найден или нет tg_id.")
        return

    await state.update_data(
        items=[],
        client_id=client_info['tg_id'],
        client_excel_id=f"FS{internal_id:04d}",
        form_title="Таможенный Бланк (Админ)"
    )

    await check_missing_data_and_prompt(message, state, client_info, is_admin=True)


@user_data_router.message(UserDataStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_data_collection(message, state)

    data = await state.get_data()
    client_id = data['client_id']

    # Обновляем БД и State
    await update_user_info(client_id, "name", message.text.strip())

    # Получаем обновленные данные и снова проверяем, чего не хватает
    updated_info = await get_info_profile(client_id)
    await check_missing_data_and_prompt(message, state, updated_info, is_admin=(client_id != message.from_user.id))


@user_data_router.message(UserDataStates.waiting_for_tg_link)
async def process_contact(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_data_collection(message, state)

    data = await state.get_data()
    client_id = data['client_id']

    await update_user_info(client_id, "phone", message.text.strip())  # Сохраняем как телефон

    updated_info = await get_info_profile(client_id)
    await check_missing_data_and_prompt(message, state, updated_info, is_admin=(client_id != message.from_user.id))


@user_data_router.message(UserDataStates.waiting_for_email)
async def process_email_final(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_data_collection(message, state)

    email = message.text.strip()
    if email == '-': email = "Не указано"

    await state.update_data(client_email=email)

    # Итог
    data = await state.get_data()
    user_info = await get_info_profile(data['client_id'])

    await message.answer(
        f"✅ Данные подтверждены:\n\n{format_client_info(user_info, data)}\n\n"
        "🚀 Переходим к добавлению товаров..."
    )

    # 🔥 ИМПОРТ ВНУТРИ ФУНКЦИИ - Решает проблему циклического импорта и зависания
    from order_maker.create_order import start_item_collection
    await start_item_collection(message, state)
