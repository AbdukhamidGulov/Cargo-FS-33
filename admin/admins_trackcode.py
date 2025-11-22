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


from database.db_track_admin import add_or_update_track_codes_list
from database.db_track_codes import get_all_track_codes, delete_multiple_track_codes
from keyboards import cancel_keyboard, main_keyboard
from filters_and_config import IsAdmin, admin_ids
from utils.message_common import extract_text_from_message

logger = getLogger(__name__)


class AdminTrackCodeStates(StatesGroup):
    """Состояния для обработки ввода трек-кодов в админ-панели."""
    waiting_for_codes = State()  # Ожидание ввода кодов для in_stock/shipped
    waiting_for_arrived_codes = State()  # Ожидание ввода кодов для arrived (с парсингом ID)
    waiting_for_codes_to_delete = State()  # Оставляем для совместимости с FSM ниже


admin_tc_router = Router()


# --- ПАРСИНГ КОДОВ ---

async def extract_parsed_codes(content: str, status: str) -> List[Tuple[str, Optional[int]]]:
    """
    Извлекает трек-коды и при необходимости, внутренний ID пользователя из текста или файла.
    """
    codes_data = []
    lines = list(filter(None, map(str.strip, content.splitlines())))

    if status == "arrived":
        # Ожидаем формат типа FSXXXX-YYMM-Z
        for line in lines:
            match = search(r"(FS\d{4}-\d{4}-\d+)", line)
            if match:
                full_track_code = match.group(1)
                user_internal_id_match = search(r"FS(\d{4})", full_track_code)
                user_internal_id = None

                if user_internal_id_match:
                    try:
                        user_internal_id = int(user_internal_id_match.group(1))
                        codes_data.append((full_track_code, user_internal_id))
                    except ValueError:
                        logger.warning(
                            f"Не удалось преобразовать ID пользователя для '{full_track_code}'.")
                else:
                    logger.warning(f"Не найден ID в трек-коде 'прибывший': '{full_track_code}'.")
            else:
                logger.warning(f"Не удалось распарсить 'прибывший' трек-код из строки: '{line}'.")
    else:
        # Для in_stock и shipped просто извлекаем код
        for line in lines:
            if line:
                codes_data.append((line, None))

    return codes_data


# --- ДОБАВЛЕНИЕ ТРЕК-КОДОВ ---

@admin_tc_router.message(F.text == "️Добавить прибывшие на склад трек-коды", IsAdmin(admin_ids))
async def add_in_stock_track_codes(message: Message, state: FSMContext):
    await message.answer("Отправьте список кодов (текст/файл) для статуса <b>На складе</b>.",
                         reply_markup=cancel_keyboard)
    await state.set_state(AdminTrackCodeStates.waiting_for_codes)
    await state.update_data(status="in_stock")


@admin_tc_router.message(F.text == "Добавить отправленные трек-коды", IsAdmin(admin_ids))
async def add_shipped_track_codes(message: Message, state: FSMContext):
    await message.answer("Отправьте список кодов (текст/файл) для статуса <b>Отправлен</b>.",
                         reply_markup=cancel_keyboard)
    await state.set_state(AdminTrackCodeStates.waiting_for_codes)
    await state.update_data(status="shipped")


@admin_tc_router.message(F.text == "Добавить прибывшие посылки", IsAdmin(admin_ids))
async def add_arrived_track_codes(message: Message, state: FSMContext):
    await message.answer(
        "Отправьте список кодов (<code>FSXXXX-YYMM-Z</code>) для статуса <b>Прибыл</b>.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(AdminTrackCodeStates.waiting_for_arrived_codes)
    await state.update_data(status="arrived")


@admin_tc_router.message(AdminTrackCodeStates.waiting_for_codes)
@admin_tc_router.message(AdminTrackCodeStates.waiting_for_arrived_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает ввод трек-кодов, добавляя или обновляя их в базе данных."""

    # 1. Используем обновленный extract_text_from_message
    content = await extract_text_from_message(message, bot)

    if not content:
        # Если файл не читается, extract_text_from_message уже отправил ошибку
        await state.clear()
        return

    data = await state.get_data()
    status = data.get("status")

    codes_to_process: List[Tuple[str, Optional[int]]] = await extract_parsed_codes(content, status)

    if not codes_to_process:
        await message.answer("Не удалось получить трек-коды. Проверьте формат.", reply_markup=cancel_keyboard)
        return

    status_display = {
        "in_stock": ("На складе", "добавлено/обновлено"),
        "shipped": ("Отправлен", "обновлено"),
        "arrived": ("Прибыл на место назначения", "обновлено")
    }.get(status, ("", ""))

    status_display_text, action_text = status_display

    # 2. Вызываем функцию сложной логики из db_track_admin
    await add_or_update_track_codes_list(codes_to_process, status, bot)

    await message.answer(
        f"✅ Успешно {action_text} <b>{len(codes_to_process)}</b> трек-кодов со статусом '<b>{status_display_text}</b>'.",
        reply_markup=main_keyboard
    )
    await state.clear()


# --- УДАЛЕНИЕ ТРЕК-КОДОВ (По списку) ---

@admin_tc_router.message(F.text == "Удалить трек-коды", IsAdmin(admin_ids))
async def delete_track_codes_start(message: Message, state: FSMContext):
    await message.answer("Отправьте один или несколько трек-кодов для удаления (текст/файл):",
                         reply_markup=cancel_keyboard)
    await state.set_state(AdminTrackCodeStates.waiting_for_codes_to_delete)


@admin_tc_router.message(AdminTrackCodeStates.waiting_for_codes_to_delete)
async def process_track_codes_deletion(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() == "отмена":
        await message.answer("Удаление трек-кодов отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    # Теперь поддерживаем и файлы для удаления
    content = await extract_text_from_message(message, bot)

    if not content:
        if not message.document:
            await message.answer("Не удалось получить трек-коды. Попробуйте снова.", reply_markup=cancel_keyboard)
        return

    codes_to_delete = [line.strip() for line in content.splitlines() if line.strip()]
    total_count = len(codes_to_delete)

    if not codes_to_delete:
        await message.answer("Не найдено трек-кодов для удаления.", reply_markup=cancel_keyboard)
        return

    try:
        # 3. Вызываем функцию базовой БД из db_track_codes
        deleted_count = await delete_multiple_track_codes(codes_to_delete)
        failed_count = total_count - deleted_count

        response_text = f"✅ Результат удаления из <b>{total_count}</b> указанных кодов:\n"
        response_text += f"— Успешно удалено: <b>{deleted_count}</b>."

        if failed_count > 0:
            response_text += f"\n— Не найдено в БД: <b>{failed_count}</b>."

        await message.answer(response_text, reply_markup=main_keyboard)
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при удалении трек-кодов: {e}")
        await message.answer("Произошла ошибка при удалении.", reply_markup=main_keyboard)
        await state.clear()


# --- ПОЛУЧЕНИЕ СПИСКА ТРЕК-КОДОВ (ОТЧЕТ) ---

async def generate_track_codes_report(track_codes: list) -> Tuple[str, str]:
    """Генерирует Excel и текстовый файлы со списком трек-кодов."""
    excel_file_path = "track_codes.xlsx"
    text_file_path = "track_codes.txt"
    excel_workbook = Workbook()
    sheet = excel_workbook.active
    sheet.title = "Track Codes"

    headers = ["ID", "Track Code", "Status", "User TG_ID"]
    sheet.append(headers)

    # Применяем стили к заголовкам
    for col in sheet.iter_cols(min_row=1, max_row=1, min_col=1, max_col=len(headers)):
        for cell in col:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write("Список трек-кодов\n" + "=" * 40 + "\n")

        for row in track_codes:
            # Принимаем, что row - это словарь, как возвращает get_all_track_codes
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

    # 4. Вызываем новую функцию get_all_track_codes из db_track_codes
    track_codes = await get_all_track_codes()

    if not track_codes:
        await message.answer("База трек-кодов пуста. Отчет не сгенерирован.", reply_markup=main_keyboard)
        return

    excel_file_path, text_file_path = await generate_track_codes_report(track_codes)
    excel_file_input = FSInputFile(excel_file_path)
    text_file_input = FSInputFile(text_file_path)

    await message.answer_document(excel_file_input)
    await message.answer_document(text_file_input)

    # Очистка временных файлов
    remove(excel_file_path)
    remove(text_file_path)
