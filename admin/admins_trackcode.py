from logging import getLogger
from typing import Optional, List, Tuple
from os import remove
from re import search

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook

from database.db_track_admin import (
    add_or_update_track_codes_list,
    get_track_codes_list,
    bulk_delete_track_codes
)
from keyboards import cancel_keyboard, main_keyboard
from filters_and_config import IsAdmin, admin_ids
from utils.message_common import extract_text_from_message

logger = getLogger(__name__)


# Определение состояний FSM для этого модуля с уникальным именем
class AdminTrackCodeStates(StatesGroup):
    """Состояния для обработки ввода трек-кодов в админ-панели."""
    waiting_for_codes = State()  # Ожидание ввода кодов для in_stock/shipped
    waiting_for_arrived_codes = State()  # Ожидание ввода кодов для arrived (с парсингом ID)
    waiting_for_codes_to_delete = State()  # Ожидание ввода кодов для удаления


admin_tc_router = Router()


# Функция для извлечения и парсинга трек-кодов
async def extract_parsed_codes(content: str, status: str) -> List[Tuple[str, Optional[int]]]:
    """
    Извлекает трек-коды и при необходимости, внутренний ID пользователя из текста или файла.
    """
    codes_data = []
    lines = list(filter(None, map(str.strip, content.splitlines())))

    if status == "arrived":
        # Ожидаем формат типа FSXXXX-YYMM-Z
        for line in lines:
            # Ищем шаблон FSXXXX, чтобы извлечь ID пользователя
            match = search(r"(FS\d{4}-\d{4}-\d+)", line)
            if match:
                full_track_code = match.group(1)
                # Ищем внутренний ID пользователя в коде (XXXX в FSXXXX)
                user_internal_id_match = search(r"FS(\d{4})", full_track_code)

                if user_internal_id_match:
                    user_internal_id_str = user_internal_id_match.group(1)
                    try:
                        user_internal_id = int(user_internal_id_str)
                        codes_data.append((full_track_code, user_internal_id))
                    except ValueError:
                        logger.warning(
                            f"Не удалось преобразовать внутренний ID пользователя '{user_internal_id_str}' в число для трек-кода '{full_track_code}'. Пропускаем.")
                else:
                    logger.warning(f"Не найден внутренний ID в трек-коде 'прибывший': '{full_track_code}'. Пропускаем.")
            else:
                logger.warning(f"Не удалось распарсить 'прибывший' трек-код из строки: '{line}'. Пропускаем.")
    else:
        # Для in_stock и shipped просто извлекаем код
        for line in lines:
            if line:
                codes_data.append((line, None))
    return codes_data


# ************************************************
# ДОБАВЛЕНИЕ ТРЕК-КОДОВ (in_stock, shipped, arrived)
# ************************************************

@admin_tc_router.message(F.text == "️Добавить пребывшие на склад трек-коды", IsAdmin(admin_ids))
async def add_in_stock_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления трек-кодов, находящихся на складе."""
    await message.answer("Пожалуйста, отправьте список трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(AdminTrackCodeStates.waiting_for_codes)
    await state.update_data(status="in_stock")


@admin_tc_router.message(F.text == "Добавить отправленные трек-коды", IsAdmin(admin_ids))
async def add_shipped_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления отправленных трек-кодов."""
    await message.answer("Отправьте список отправленных трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(AdminTrackCodeStates.waiting_for_codes)
    await state.update_data(status="shipped")


@admin_tc_router.message(F.text == "Добавить прибывшие посылки", IsAdmin(admin_ids))
async def add_arrived_track_codes(message: Message, state: FSMContext):
    """Начинает процесс добавления трек-кодов, прибывших на место назначения."""
    await message.answer(
        "Отправьте список трек-кодов, прибывших на место назначения (формат: <code>FSXXXX-YYMM-Z</code>) "
        "или загрузите файл (.txt).\n"
        "<i>(каждый трек-код с новой строки)</i>.")
    await state.set_state(AdminTrackCodeStates.waiting_for_arrived_codes)
    await state.update_data(status="arrived")


@admin_tc_router.message(AdminTrackCodeStates.waiting_for_codes)
@admin_tc_router.message(AdminTrackCodeStates.waiting_for_arrived_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает ввод трек-кодов, добавляя или обновляя их в базе данных."""
    # 1. Используем утилиту для извлечения текста (из Message или Document)
    content = await extract_text_from_message(message, bot)

    if not content:
        # Утилита сама отправляет сообщение об ошибке, если файл не читается
        await state.clear()
        return

    data = await state.get_data()
    status = data.get("status")

    # Парсинг данных
    codes_to_process: List[Tuple[str, Optional[int]]] = await extract_parsed_codes(content, status)

    if not codes_to_process:
        await message.answer(
            "Не удалось получить трек-коды. Убедитесь, что отправили текст или файл с кодами в правильном формате.")
        await state.clear()
        return

    action_text = "добавлено"
    status_display_text = ""
    if status == "in_stock":
        status_display_text = "На складе"
    elif status == "shipped":
        status_display_text = "Отправлен"
        action_text = "обновлено"
    elif status == "arrived":
        status_display_text = "Прибыл на место назначения"
        action_text = "обновлено"

    # Добавление/обновление в БД
    await add_or_update_track_codes_list(codes_to_process, status, bot)

    await message.answer(
        f"Успешно {action_text} {len(codes_to_process)} трек-кодов со статусом '{status_display_text}'.")
    await state.clear()


# ************************************************
# УДАЛЕНИЕ ТРЕК-КОДОВ
# ************************************************

@admin_tc_router.message(F.text == "Удалить трек-коды", IsAdmin(admin_ids))
async def delete_track_codes_start(message: Message, state: FSMContext):
    """Начинает процесс удаления трек-кодов, запрашивая список."""
    await message.answer("Пожалуйста, отправьте один или несколько трек-кодов, которые нужно удалить:\n"
                         "<i>(каждый трек-код с новой строки)</i>.",
                         reply_markup=cancel_keyboard)
    await state.set_state(AdminTrackCodeStates.waiting_for_codes_to_delete)


@admin_tc_router.message(AdminTrackCodeStates.waiting_for_codes_to_delete)
async def process_track_codes_deletion(message: Message, state: FSMContext):
    """Обрабатывает введенный список трек-кодов и удаляет их из базы данных."""
    if message.text == "Отмена":
        await message.answer("Удаление трек-кодов отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    codes_to_delete = list(filter(None, map(str.strip, message.text.splitlines())))
    total_count = len(codes_to_delete)

    if not codes_to_delete:
        await message.answer(
            "Не удалось получить трек-коды для удаления. Пожалуйста, введите коды (каждый с новой строки) или нажмите 'Отмена'.",
            reply_markup=cancel_keyboard)
        return

    try:
        # Используем функцию, возвращающую (удалено, не найдено)
        deleted_count, failed_count = await bulk_delete_track_codes(codes_to_delete)

        response_text = f"✅ Результат удаления из <b>{total_count}</b> указанных кодов:\n"
        response_text += f"— Успешно удалено: <b>{deleted_count}</b>."

        if failed_count > 0:
            response_text += f"\n— Не найдено в БД: <b>{failed_count}</b>."

        await message.answer(
            response_text,
            reply_markup=main_keyboard
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при удалении трек-кодов: {e}")
        await message.answer("Произошла ошибка при удалении трек-кодов. Попробуйте позже.", reply_markup=main_keyboard)
        await state.clear()


# ************************************************
# ПОЛУЧЕНИЕ СПИСКА ТРЕК-КОДОВ (ОТЧЕТ)
# ************************************************

async def generate_track_codes_report(track_codes: list, users: dict) -> Tuple[str, str]:
    """Генерирует Excel и текстовый файлы со списком трек-кодов."""
    excel_file_path = "track_codes.xlsx"
    text_file_path = "track_codes.txt"
    excel_workbook = Workbook()
    sheet = excel_workbook.active
    sheet.title = "Track Codes"

    headers = ["ID", "Track Code", "Status", "User TG_ID"]
    sheet.append(headers)
    for col in sheet.iter_cols(min_row=1, max_row=1, min_col=1, max_col=len(headers)):
        for cell in col:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write("Список трек-кодов\n")
        text_file.write("=" * 40 + "\n")
        for row in track_codes:
            user_info = f"TG_ID: {row['tg_id']}" if row["tg_id"] else "Не привязан"
            sheet.append([row["id"], row["track_code"], row["status"], user_info])
            text_file.write(
                f"{row['id']:03d}. Track Code: {row['track_code']}, Status: {row['status']}, User: {user_info}\n")

    excel_workbook.save(excel_file_path)
    return excel_file_path, text_file_path


@admin_tc_router.message(F.text == "Список трек-кодов", IsAdmin(admin_ids))
async def generate_track_codes_list(message: Message):
    """Генерирует и отправляет список всех трек-кодов в виде Excel и текстового файла."""
    await message.delete()
    track_codes = await get_track_codes_list()

    excel_file_path, text_file_path = await generate_track_codes_report(track_codes, {})
    excel_file_input = FSInputFile(excel_file_path)
    text_file_input = FSInputFile(text_file_path)

    await message.answer_document(excel_file_input)
    await message.answer_document(text_file_input)

    # Очистка временных файлов
    remove(excel_file_path)
    remove(text_file_path)
