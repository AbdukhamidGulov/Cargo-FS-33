from os import remove
from logging import getLogger

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile, CallbackQuery
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook

from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard, confirm_keyboard
from database.base import setup_database
from database.users import get_user_by_id, get_users_tg_info, drop_users_table
from database.track_codes import add_or_update_track_codes_list, get_track_codes_list, delete_shipped_track_codes, \
    drop_track_codes_table
admin_router = Router()
logger = getLogger(__name__)

@admin_router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Открывает панель администратора с выбором команд при нажатии на соответствующую кнопку."""
    await callback.message.answer("Выберите команду", reply_markup=admin_keyboard)
    await callback.answer()

@admin_router.message(F.text.lower() == "админ", IsAdmin(admin_ids))
@admin_router.message(Command(commands=['admin_router']), IsAdmin(admin_ids))
async def admin_menu(message: Message):
    """Обрабатывает команду /admin_router для администраторов, показывая меню команд."""
    await message.answer('Выберите команду', reply_markup=admin_keyboard)

@admin_router.message(Command(commands=['admin_router']))
async def handle_non_admin_attempt(message: Message, bot: Bot):
    """Обрабатывает команду /admin_router для неадминов, уведомляя их об отсутствии прав и сообщая первому админу о попытке."""
    await message.answer('Вы не являетесь админом')
    await bot.send_message(admin_ids[0], text=f"Пользователь {message.from_user.username} "
                                              f"с id <code>{message.from_user.id}</code> нажал на команду <b>admin_router</b>")

# Искать информацию по ID
class SearchUserStates(StatesGroup):
    waiting_for_user_id = State()

@admin_router.message(F.text == "Искать информацию по ID")
async def start_user_search(message: Message, state: FSMContext):
    """Начинает процесс поиска информации о пользователе по ID, запрашивая ввод ID."""
    await message.answer("Введите ID пользователя (например, FS0001 или просто 1):")
    await state.set_state(SearchUserStates.waiting_for_user_id)

@admin_router.message(SearchUserStates.waiting_for_user_id)
async def process_user_search_input(message: Message, state: FSMContext):
    """Обрабатывает введенный ID пользователя, возвращая его данные или сообщение об ошибке."""
    user_id = message.text.strip()
    user_data = await get_user_by_id(user_id)

    if not user_data:
        await message.answer("Пользователь с таким ID не найден.")
        await state.clear()
        return

    no_value = "<i>Не заполнено</i>"
    await message.answer(
        f"ID: <code>FS{user_data['id']:04d}</code>\n"
        f"Имя: {user_data['name'] or no_value}\n"
        f"Username: @{user_data['username'] or no_value}\n"
        f"Номер телефона: {user_data['phone'] or no_value}\n"
    )
    await state.clear()

# Добавить трек-номера
class TrackCodeStates(StatesGroup):
    waiting_for_codes = State()

async def extract_track_codes_from_text(message: Message) -> list[str]:
    """Извлекает трек-коды из текстового сообщения, разделяя их по пробелам или строкам."""
    return list(filter(None, map(str.strip, message.text.split())))

async def extract_track_codes_from_file(message: Message, bot: Bot) -> list[str]:
    """Извлекает трек-коды из загруженного текстового файла."""
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_content = await bot.download_file(file_path)
    content = file_content.read().decode('utf-8')
    return list(filter(None, map(str.strip, content.splitlines())))

async def process_track_codes(message: Message, state: FSMContext, status: str, bot: Bot):
    """Обрабатывает ввод трек-кодов, добавляя или обновляя их в базе данных."""
    track_codes = []
    if message.text:
        track_codes = await extract_track_codes_from_text(message)
    elif message.document:
        track_codes = await extract_track_codes_from_file(message, bot)

    if not track_codes:
        await message.answer("Не удалось получить трек-коды. Убедитесь, что отправили текст или текстовый файл с кодами.")
        return

    action = "добавлено" if status == "in_stock" else "обновлено"
    status_text = "На складе" if status == "in_stock" else "Отправлен"


    await add_or_update_track_codes_list(track_codes, status, bot, message)
    await message.answer(f"Успешно {action} {len(track_codes)} трек-кодов в базу данных со статусом '{status_text}'.")
    await state.clear()

@admin_router.message(F.text == "️Добавить пребывшие на склад трек-коды", IsAdmin(admin_ids))
async def add_in_stock_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления трек-кодов, находящихся на складе, запрашивая ввод или файл."""
    await message.answer("Пожалуйста, отправьте список трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_codes)
    await state.update_data(status="in_stock")

@admin_router.message(F.text == "Добавить отправленные трек-коды", IsAdmin(admin_ids))
async def add_shipped_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления отправленных трек-кодов, запрашивая ввод или файл."""
    await message.answer("Отправьте список отправленных трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_codes)
    await state.update_data(status="shipped")

@admin_router.message(TrackCodeStates.waiting_for_codes)
async def process_track_codes_input(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает введенные трек-коды, вызывая функцию обработки с сохраненным статусом."""
    data = await state.get_data()
    status = data.get("status")
    await process_track_codes(message, state, status, bot)

# Получение списка трек-кодов
async def generate_track_codes_report(track_codes: list, users: dict) -> tuple[str, str]:
    """Генерирует Excel и текстовый файлы со списком трек-кодов."""
    excel_file_path = "track_codes.xlsx"
    text_file_path = "track_codes.txt"
    excel_workbook = Workbook()
    sheet = excel_workbook.active
    sheet.title = "Track Codes"

    headers = ["ID", "Track Code", "Status", "User"]
    sheet.append(headers)
    for col in sheet.iter_cols(min_row=1, max_row=1, min_col=1, max_col=len(headers)):
        for cell in col:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write("Список трек-кодов\n")
        text_file.write("=" * 40 + "\n")
        for row in track_codes:
            user_link = f"t.me/{users.get(row['tg_id'], '')}" if row["tg_id"] else "—"
            sheet.append([row["id"], row["track_code"], row["status"], user_link])
            text_file.write(f"{row['id']:03d}. Track Code: {row['track_code']}, Status: {row['status']}, User: {user_link}\n")

    excel_workbook.save(excel_file_path)
    return excel_file_path, text_file_path

@admin_router.message(F.text == "️Список трек-кодов", IsAdmin(admin_ids))
async def generate_track_codes_list(message: Message):
    """Генерирует и отправляет список всех трек-кодов в виде Excel и текстового файла."""
    await message.delete()
    track_codes = await get_track_codes_list()
    users = await get_users_tg_info()

    excel_file_path, text_file_path = await generate_track_codes_report(track_codes, users)
    excel_file_input = FSInputFile(excel_file_path)
    text_file_input = FSInputFile(text_file_path)

    await message.answer_document(excel_file_input)
    await message.answer_document(text_file_input)

    remove(excel_file_path)
    remove(text_file_path)

# Обработка функций для удаления с подтверждением
class DangerActions(StatesGroup):
    confirm_action = State()

@admin_router.message(F.text == "Удалить отправленные трек-коды", IsAdmin(admin_ids))
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

# Функции для улавливания токенов файлов
@admin_router.message(F.photo, IsAdmin(admin_ids))
async def capture_photo_token(message: Message):
    """Отправляет токен ID загруженного фото администратору."""
    photo_token = message.photo[0].file_id
    await message.reply(f"<b>Токен скинутого фото:</b>\n<code>{photo_token}</code>")

@admin_router.message(F.video, IsAdmin(admin_ids))
async def capture_video_token(message: Message):
    """Отправляет токен ID загруженного видео администратору."""
    video_token = message.video.file_id
    await message.reply(f"<b>Токен скинутого видео:</b>\n<code>{video_token}</code>")

@admin_router.message(F.document)
async def capture_document_token(message: Message):
    """Отправляет токен ID загруженного документа администратору."""
    document_token = message.document.file_id
    await message.reply(f"<b>Токен скинутого документа:</b>\n<code>{document_token}</code>")
