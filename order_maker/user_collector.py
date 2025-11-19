from logging import getLogger
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from typing import Dict, Any

from database.db_users import get_info_profile, update_user_info, get_user_by_id
from keyboards import cancel_keyboard, main_keyboard
from filters_and_config import admin_ids

from order_maker.create_order import start_item_collection

user_data_router = Router()
logger = getLogger(__name__)


class UserDataStates(StatesGroup):
    """Состояния для сбора информации о пользователе."""
    waiting_for_name = State()
    waiting_for_tg_link = State()
    waiting_for_email = State()
    admin_waiting_for_client_code = State()


def format_client_info(user_info: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Форматирует информацию о клиенте для вывода, используя данные из БД и FSM."""
    name = user_info.get('name', '❌ Не заполнено') or '❌ Не заполнено'
    username = user_info.get('username')
    phone = user_info.get('phone')

    name = data.get('client_name', name)
    email = data.get('client_email', '❓ Будет запрошен')
    fs_code = data.get("client_excel_id", "N/A")

    if username:
        tg_contact = f"@{username}"
    elif phone:
        tg_contact = phone
    else:
        tg_contact = '❌ Не заполнено'

    tg_contact = data.get('client_tg', tg_contact)

    return (
        f"📝 <b>Данные для бланка:</b>\n\n"
        f"<b>Код клиента:</b> {fs_code}\n"
        f"<b>Имя:</b> {name}\n"
        f"<b>Контакт (TG/Тел):</b> {tg_contact}\n"
        f"<b>Email:</b> {email}\n"
    )


# --- ТОЧКА ВХОДА (ОБЩАЯ) ---

@user_data_router.callback_query(F.data == "customs_form_filling") 
async def start_order_process(callback: CallbackQuery, state: FSMContext): 
    """
    Точка входа (по инлайн-кнопке "Заполнение бланка Таможни").
    Разделяет логику для админа и обычного пользователя.
    """
    user_id = callback.from_user.id 

    await state.clear()

    is_admin = user_id in admin_ids

    if is_admin:
        await callback.message.answer( 
            "💻 <b>Режим Администратора: Заполнение Бланка</b>\n\n"
            "Пожалуйста, введите <b>ID пользователя</b> (числовой или в формате FSXXXX), для которого заполняете бланк:",
            reply_markup=cancel_keyboard
        )
        await state.set_state(UserDataStates.admin_waiting_for_client_code)
    else:
        # Логика для обычного пользователя
        user_info = await get_info_profile(user_id)
        if not user_info:
            await callback.message.answer("Ошибка: Профиль не найден. Пожалуйста, нажмите /start.") 
            return

        fs_code = f"FS{user_info['id']:04d}"

        await state.update_data(
            items=[],
            client_id=user_id,
            client_excel_id=fs_code,
            form_title="Таможенный Бланк"
        )

        await callback.message.answer("📝 Начинаем заполнение Таможенного Бланка...") 
        await process_client_data_check(callback.message, state, user_id, user_info)
    
    await callback.answer() 


# --- ЛОГИКА ДЛЯ АДМИНИСТРАТОРА ---

@user_data_router.message(UserDataStates.admin_waiting_for_client_code, F.text)
async def admin_process_client_code(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    query = message.text.strip()
    internal_id = None

    # Парсим FSXXXX или XXXX в число
    if query.startswith("FS") and len(query) == 6 and query[2:].isdigit():
        internal_id = int(query[2:])
    elif query.isdigit():
        internal_id = int(query)
    else:
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите числовой ID пользователя или в формате FSXXXX.",
            reply_markup=cancel_keyboard
        )
        return

    client_info = await get_user_by_id(internal_id)

    if not client_info:
        await message.answer(
            f"❌ Клиент с ID <b>{query}</b> не найден в базе данных.",
            reply_markup=cancel_keyboard
        )
        return

    client_tg_id = client_info.get('tg_id')
    if not client_tg_id:
        await message.answer("Ошибка: В данных клиента отсутствует tg_id.")
        return

    fs_code = f"FS{client_info['id']:04d}"

    await state.update_data(
        items=[],
        client_id=client_tg_id,
        client_excel_id=fs_code,
        form_title="Таможенный Бланк (Админ)"
    )

    await process_client_data_check(message, state, client_tg_id, client_info, is_admin_mode=True)


# --- ЛОГИКА ПРОВЕРКИ ДАННЫХ (ОБЩАЯ) ---

async def process_client_data_check(message: Message, state: FSMContext, user_id: int, user_info: dict,
                                    is_admin_mode: bool = False):
    """
    Проверяет, какие данные (имя, контакт) отсутствуют, и запрашивает их.
    """
    prefix = "📦 <b>Создание Бланка Заказа</b>\n\n" if not is_admin_mode else "✍️ <b>Заполнение данных клиента</b>\n\n"

    # 1. Проверка Имени
    name = user_info.get('name')
    if not name:
        await message.answer(
            f"{prefix}"
            "Мне нужно <b>Имя</b> клиента для заполнения бланка.\n"
            "Пожалуйста, введите его:",
            reply_markup=cancel_keyboard
        )
        await state.set_state(UserDataStates.waiting_for_name)
        return

    await state.update_data(client_name=name)

    # 2. Проверка Username или Phone
    username = user_info.get('username')
    phone = user_info.get('phone')

    if not username and not phone:
        await message.answer(
            f"{prefix}"
            "У клиента не установлен Username и нет телефона. Пожалуйста, отправьте <b>ссылку на Telegram</b> (или номер телефона):",
            reply_markup=cancel_keyboard
        )
        await state.set_state(UserDataStates.waiting_for_tg_link)
        return

    contact_value = f"@{username}" if username else phone
    await state.update_data(client_tg=contact_value)

    # 3. Запрос Email (всегда, т.к. его нет в БД)
    await ask_for_email(message, state)


async def ask_for_email(message: Message, state: FSMContext):
    """Вспомогательная функция запроса почты."""
    await message.answer(
        "📧 Введите <b>электронную почту</b> для связи (можно пропустить, введя '-'):",
        reply_markup=cancel_keyboard
    )
    await state.set_state(UserDataStates.waiting_for_email)


async def cancel_data_collection(message: Message, state: FSMContext):
    """Отмена сбора данных."""
    await message.answer("Создание бланка отменено.", reply_markup=main_keyboard)
    await state.clear()


# --- ХЕНДЛЕРЫ FSM ---

@user_data_router.message(UserDataStates.waiting_for_name, F.text)
async def process_name_input(message: Message, state: FSMContext):
    """Сохраняет имя и продолжает проверку."""
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    new_name = message.text.strip()
    data = await state.get_data()
    client_id = data.get('client_id')  # Это TG ID

    await update_user_info(client_id, "name", new_name)
    await state.update_data(client_name=new_name)

    user_info = await get_info_profile(client_id)
    await process_client_data_check(message, state, client_id, user_info,
                                    is_admin_mode=client_id != message.from_user.id)


@user_data_router.message(UserDataStates.waiting_for_tg_link, F.text)
async def process_tg_input(message: Message, state: FSMContext):
    """Сохраняет контакт (в поле phone) и продолжает проверку."""
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    new_tg_contact = message.text.strip()
    data = await state.get_data()
    client_id = data.get('client_id')  # Это TG ID

    # Сохраняем кастомный контакт в поле 'phone'
    await update_user_info(client_id, "phone", new_tg_contact)
    await state.update_data(client_tg=new_tg_contact)

    user_info = await get_info_profile(client_id)
    await process_client_data_check(message, state, client_id, user_info,
                                    is_admin_mode=client_id != message.from_user.id)


@user_data_router.message(UserDataStates.waiting_for_email, F.text)
async def process_email_input(message: Message, state: FSMContext):
    """Сохраняет Email и переходит к сбору товаров."""
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    client_email = message.text.strip()
    if client_email == '-':
        client_email = "Не указано"

    await state.update_data(client_email=client_email)

    # ВСЕ ДАННЫЕ СОБРАНЫ
    data = await state.get_data()
    user_info = await get_info_profile(data.get('client_id'))
    info_text = format_client_info(user_info, data)

    await message.answer(
        f"✅ Данные клиента подтверждены:\n\n{info_text}\n\n"
        "Начинаем сбор товаров..."
    )
    # ПЕРЕХОДИМ К СБОРУ ТОВАРОВ
    await start_item_collection(message, state)