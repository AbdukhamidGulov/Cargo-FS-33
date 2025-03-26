from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook
from logging import getLogger
from os import remove

from database.track_codes import add_or_update_track_codes_list, get_track_codes_list
from database.users import get_users_tg_info
from filters_and_config import IsAdmin, admin_ids

admin_tc_router = Router()
logger = getLogger(__name__)

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


@admin_tc_router.message(F.text == "️Добавить пребывшие на склад трек-коды", IsAdmin(admin_ids))
async def add_in_stock_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления трек-кодов, находящихся на складе, запрашивая ввод или файл."""
    await message.answer("Пожалуйста, отправьте список трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_codes)
    await state.update_data(status="in_stock")
    logger.debug("Старт процесс добавления трек-кодов, находящихся на складе, запрашивая ввод или файл.")


@admin_tc_router.message(F.text == "Добавить отправленные трек-коды", IsAdmin(admin_ids))
async def add_shipped_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления отправленных трек-кодов, запрашивая ввод или файл."""
    await message.answer("Отправьте список отправленных трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_codes)
    await state.update_data(status="shipped")


@admin_tc_router.message(TrackCodeStates.waiting_for_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает ввод трек-кодов, добавляя или обновляя их в базе данных."""
    data = await state.get_data()
    status = data.get("status")  # Получаем статус из состояния
    track_codes = []
    if message.text:
        track_codes = await extract_track_codes_from_text(message)  # Извлекаем из текста
    elif message.document:
        track_codes = await extract_track_codes_from_file(message, bot)  # Извлекаем из файла

    if not track_codes:
        await message.answer("Не удалось получить трек-коды. Убедитесь, что отправили текст или файл с кодами.")
        return

    action = "добавлено" if status == "in_stock" else "обновлено"  # Определяем действие
    status_text = "На складе" if status == "in_stock" else "Отправлен"  # Текст статуса

    # Обрабатываем трек-коды и отправляем уведомления внутри функции
    await add_or_update_track_codes_list(track_codes, status, bot)

    await message.answer(f"Успешно {action} {len(track_codes)} трек-кодов со статусом '{status_text}'.")
    await state.clear()  # Очищаем состояние


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


@admin_tc_router.message(F.text == "Список трек-кодов")
async def generate_track_codes_list(message: Message):
    """Генерирует и отправляет список всех трек-кодов в виде Excel и текстового файла."""
    logger.debug(IsAdmin(admin_ids))
    logger.debug(admin_ids)
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
