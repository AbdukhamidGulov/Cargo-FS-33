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


class UserDataStates(StatesGroup):
    """Состояния для сбора информации о пользователе (для Таможенного Бланка)."""
    # Общие состояния для клиента/админа
    waiting_for_name = State()
    waiting_for_tg_link = State()
    waiting_for_email = State()

    # Состояния для режима АДМИНИСТРАТОРА
    admin_waiting_for_client_code = State()
    admin_confirm_data = State()


def format_client_info(user_info: Dict[str, Any], form_title: str) -> str:
    """Форматирует информацию о клиенте для вывода, используя только доступные поля."""
    name = user_info.get('name', '❌ Не заполнено') or '❌ Не заполнено'
    username = user_info.get('username')
    phone = user_info.get('phone')

    # Приоритет отображения: Username > Phone > 'Не заполнено'
    if username:
        tg_contact = f"@{username}"
    elif phone:
        tg_contact = phone
    else:
        tg_contact = '❌ Не заполнено'

    # Email берем из контекста FSM, так как в DB его нет, но здесь пока отображаем заглушку
    email = '❓ Будет запрошен'

    return (
        f"📝 <b>{form_title}</b>\n\n"
        f"<b>Клиент:</b>\n"
        f"— Telegram ID: <code>{user_info.get('tg_id')}</code>\n"
        f"— Имя: <b>{name}</b>\n"
        f"— Контакт Telegram/Phone: <b>{tg_contact}</b>\n"
        f"— Email (только для заказа): <b>{email}</b>\n"
    )


# --- ТОЧКА ВХОДА (ОБЩАЯ) ---

@user_data_router.callback_query(F.data == "customs_form_filling")
async def start_order_process(query: CallbackQuery, state: FSMContext):
    """
    Точка входа (по callback_query 'customs_form_filling').
    Разделяет логику для админа и обычного пользователя.
    """
    # Подтверждаем callback
    await query.answer()

    message = query.message
    user_id = query.from_user.id

    await state.clear()
    await state.update_data(
        items=[],
        client_id=user_id,
        form_type="customs",
        form_title="Таможенный Бланк"
    )

    is_admin = user_id in admin_ids

    if is_admin:
        await message.answer(
            "💻 <b>Режим Администратора: Заполнение Таможенного Бланка</b>\n\n"
            "Пожалуйста, введите <b>ID пользователя</b> (числовой или в формате FSXXXX), для которого заполняете бланк:",
            reply_markup=cancel_keyboard
        )
        await state.set_state(UserDataStates.admin_waiting_for_client_code)
    else:
        # Логика для обычного пользователя
        # Отправляем сообщение, так как inline-кнопка исчезнет
        await message.answer("📝 Начинаем заполнение Таможенного Бланка...")
        await process_client_data_check(message, state, user_id)


# --- ЛОГИКА ДЛЯ АДМИНИСТРАТОРА ---

@user_data_router.message(UserDataStates.admin_waiting_for_client_code, F.text)
async def admin_process_client_code(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    query = message.text.strip()

    # Проверка формата
    if not (query.isdigit() or (query.startswith('FS') and len(query) == 6 and query[2:].isdigit())):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите числовой ID пользователя или в формате FSXXXX."
            "\nИли напишите <code>Отмена</code> чтобы остановить режим поиска по ID",
            reply_markup=cancel_keyboard
        )
        return

    # Получаем информацию о клиенте по ID (числовому или FS-коду)
    client_info = await get_user_by_id(query)

    if not client_info:
        await message.answer(
            f"❌ Клиент с ID/кодом <b>{query}</b> не найден в базе данных.\n"
            f"Попробуйте ввести другой ID/код или отмените."
        )
        return

    # Используем tg_id как основной идентификатор для дальнейших операций
    client_id = client_info.get('tg_id')
    if not client_id:
        await message.answer("Ошибка: В данных клиента отсутствует tg_id.")
        return

    # Сохраняем ID клиента и текущие данные в контекст
    await state.update_data(
        client_id=client_id,
        client_name=client_info.get('name'),
        client_tg=client_info.get('username') or client_info.get('phone')
    )

    # Вывод текущих данных клиента
    info_text = format_client_info(client_info, "Данные Клиента для Таможенного Бланка")

    await message.answer(
        f"✅ Клиент найден. Текущие данные:\n\n{info_text}",
        reply_markup=cancel_keyboard
    )

    # Запускаем проверку данных для заполнения
    await process_client_data_check(message, state, client_id, is_admin_mode=True)


# --- ЛОГИКА ПРОВЕРКИ ДАННЫХ (ОБЩАЯ, ИСПОЛЬЗУЕТСЯ ДЛЯ КЛИЕНТА И АДМИНА) ---

async def process_client_data_check(message: Message, state: FSMContext, user_id: int, is_admin_mode: bool = False):
    """
    Проверяет, какие данные (имя, ТГ-контакт/телефон) отсутствуют, и запрашивает их.
    Если данные есть - переходит к запросу email.
    """
    data = await state.get_data()
    user_info = await get_info_profile(user_id)

    if not user_info:
        await message.answer("Ошибка: Профиль клиента не найден. Пожалуйста, проверьте ID/код или нажмите /start.")
        await state.clear()
        return

    form_title = data.get('form_title', 'Бланк Заказа')
    prefix = f"📝 <b>Создание {form_title}</b>\n\n"

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

    # Сохраняем имя
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

    # Сохраняем найденный контакт в контекст (приоритет username)
    contact_value = f"@{username}" if username else phone
    await state.update_data(client_tg=contact_value)

    # 3. Запрос Email (всегда, т.к. его нет в БД)
    if not data.get('client_email'):
        await ask_for_email(message, state)
    else:
        # Все данные есть (или были собраны админом/из БД), email есть в state
        await process_email_input(message, state, skip_input=True)


async def ask_for_email(message: Message, state: FSMContext):
    """Вспомогательная функция запроса почты."""
    await message.answer(
        "📧 Введите <b>электронную почту</b> для связи (можно пропустить, введя '-'):",
        reply_markup=cancel_keyboard
    )
    await state.set_state(UserDataStates.waiting_for_email)


async def cancel_data_collection(message: Message, state: FSMContext):
    """Отмена сбора данных."""
    await message.answer("Создание заказа/бланка отменено.", reply_markup=main_keyboard)
    await state.clear()


# --- ХЕНДЛЕРЫ FSM ---

@user_data_router.message(UserDataStates.waiting_for_name, F.text)
async def process_name_input(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    new_name = message.text.strip()
    data = await state.get_data()
    client_id = data.get('client_id', message.from_user.id)

    # Обновляем имя клиента в БД
    await update_user_info(client_id, "name", new_name)
    await state.update_data(client_name=new_name)

    # Продолжаем проверку оставшихся данных
    await process_client_data_check(message, state, client_id, is_admin_mode=client_id != message.from_user.id)


@user_data_router.message(UserDataStates.waiting_for_tg_link, F.text)
async def process_tg_input(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    new_tg_contact = message.text.strip()
    data = await state.get_data()
    client_id = data.get('client_id', message.from_user.id)

    # Обновляем БД клиента: сохраняем кастомную ссылку/телефон в поле 'phone'
    await update_user_info(client_id, "phone", new_tg_contact)
    await state.update_data(client_tg=new_tg_contact)

    # Продолжаем проверку (запрос email)
    await process_client_data_check(message, state, client_id, is_admin_mode=client_id != message.from_user.id)


@user_data_router.message(UserDataStates.waiting_for_email, F.text | F.text.regexp(r'^-'))
async def process_email_input(message: Message, state: FSMContext, skip_input: bool = False):
    if message.text and message.text.lower() == "отмена":
        await cancel_data_collection(message, state)
        return

    if not skip_input:
        client_email = message.text.strip()
        if client_email == '-':
            client_email = "Не указано"

        # Email сохраняем ТОЛЬКО в контексте FSM, т.к. его нет в БД
        await state.update_data(client_email=client_email)

    # ВСЕ ДАННЫЕ СОБРАНЫ -> ПЕРЕХОДИМ К СБОРУ ТОВАРОВ
    await message.answer("✅ Данные профиля клиента подтверждены. Начинаем сбор товаров.")
    await start_item_collection(message, state)
