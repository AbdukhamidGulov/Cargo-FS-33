from logging import getLogger
from typing import Optional, List, Tuple
from os import remove

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook
from re import search


from database.track_codes import (add_or_update_track_codes_list, get_track_codes_list,
                                  delete_multiple_track_codes, get_track_code_info)
from database.users import get_info_profile
from keyboards import get_admin_edit_user_keyboard, cancel_keyboard, main_keyboard
from filters_and_config import IsAdmin, admin_ids

admin_tc_router = Router()
logger = getLogger(__name__)


# Добавить трек-номера
class TrackCodeStates(StatesGroup):
    waiting_for_codes = State()  # Для "in_stock" и "shipped"
    waiting_for_arrived_codes = State()  # Для "arrived"
    waiting_for_codes_to_delete = State()  # Состояние для удаления кодов
    waiting_for_owner_search_code = State()  # Состояние для поиска владельца по трек-коду


# Функция для извлечения и парсинга трек-кодов в зависимости от статуса
async def extract_parsed_codes(content: str, status: str) -> List[Tuple[str, Optional[int]]]:
    """
    Извлекает трек-коды и, при необходимости, внутренний ID пользователя из текста или файла.
    Возвращает список кортежей (track_code: str, user_internal_id: Optional[int]).
    """
    codes_data = []
    lines = list(filter(None, map(str.strip, content.splitlines())))

    if status == "arrived":
        for line in lines:
            match = search(r"FS(\d{4})-\d{4}-\d+", line)
            if match:
                full_track_code = match.group(0)
                user_internal_id_str = match.group(1)
                try:
                    user_internal_id = int(user_internal_id_str)
                    codes_data.append((full_track_code, user_internal_id))
                except ValueError:
                    logger.warning(
                        f"Не удалось преобразовать внутренний ID пользователя '{user_internal_id_str}' в число для трек-кода '{full_track_code}'. Пропускаем.")
            else:
                logger.warning(f"Не удалось распарсить 'прибывший' трек-код из строки: '{line}'. Пропускаем.")
    else:
        for line in lines:
            if line:
                codes_data.append((line, None))
    return codes_data


# ************************************************
# 1. ДОБАВЛЕНИЕ ТРЕК-КОДОВ (in_stock, shipped, arrived)
# ************************************************

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


@admin_tc_router.message(F.text == "Добавить прибывшие посылки", IsAdmin(admin_ids))
async def add_arrived_track_codes(message: Message, state: FSMContext):
    """
    Начинает процесс добавления трек-кодов, прибывших на место назначения.
    Запрашивает ввод или файл в специальном формате.
    """
    await message.answer(
        "Отправьте список трек-кодов, прибывших на место назначения (формат: <code>[FSXXXX-YYMM-Z]</code>) "
        "или загрузите файл (.txt).\n"
        "<i>(каждый трек-код с новой строки)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_arrived_codes)
    await state.update_data(status="arrived")
    logger.debug("Старт процесс добавления трек-кодов, прибывших на место назначения.")


@admin_tc_router.message(TrackCodeStates.waiting_for_codes)
@admin_tc_router.message(TrackCodeStates.waiting_for_arrived_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    """
    Обрабатывает ввод трек-кодов, добавляя или обновляя их в базе данных.
    Поддерживает текстовый ввод и загрузку файла, а также различные статусы.
    """
    data = await state.get_data()
    status = data.get("status")
    codes_to_process: List[Tuple[str, Optional[int]]] = []

    if message.text:
        codes_to_process = await extract_parsed_codes(message.text, status)
    elif message.document:
        try:
            file_id = message.document.file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_content = await bot.download_file(file_path)
            content = file_content.read().decode('utf-8')
            codes_to_process = await extract_parsed_codes(content, status)
        except Exception as e:
            logger.error(f"Ошибка при чтении файла трек-кодов: {e}")
            await message.answer(
                "Произошла ошибка при обработке файла. Пожалуйста, убедитесь, что это текстовый файл и попробуйте снова.")
            await state.clear()
            return

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

    await add_or_update_track_codes_list(codes_to_process, status, bot)

    await message.answer(
        f"Успешно {action_text} {len(codes_to_process)} трек-кодов со статусом '{status_display_text}'.")
    await state.clear()


# ************************************************
# 2. УДАЛЕНИЕ ТРЕК-КОДОВ
# ************************************************

@admin_tc_router.message(F.text == "Удалить трек-коды", IsAdmin(admin_ids))
async def delete_track_codes_start(message: Message, state: FSMContext):
    """Начинает процесс удаления трек-кодов, запрашивая список."""
    await message.answer("Пожалуйста, отправьте один или несколько трек-кодов, которые нужно удалить:\n"
                         "<i>(каждый трек-код с новой строки)</i>.",
                         reply_markup=cancel_keyboard)  # Добавляем клавиатуру отмены
    await state.set_state(TrackCodeStates.waiting_for_codes_to_delete)
    logger.debug("Старт процесс удаления трек-кодов.")


@admin_tc_router.message(TrackCodeStates.waiting_for_codes_to_delete)
async def process_track_codes_deletion(message: Message, state: FSMContext):
    """Обрабатывает введенный список трек-кодов и удаляет их из базы данных."""
    if message.text == "Отмена":
        await message.answer("Удаление трек-кодов отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    codes_to_delete = list(filter(None, map(str.strip, message.text.splitlines())))

    if not codes_to_delete:
        await message.answer(
            "Не удалось получить трек-коды для удаления. Пожалуйста, введите коды (каждый с новой строки) или нажмите 'Отмена'.",
            reply_markup=cancel_keyboard)
        return  # Остаемся в состоянии

    try:
        deleted_count = await delete_multiple_track_codes(codes_to_delete)
        await message.answer(
            f"✅ Успешно удалено <b>{deleted_count}</b> трек-кодов из <b>{len(codes_to_delete)}</b> указанных.",
            reply_markup=main_keyboard
        )
        logger.info(f"Админ {message.from_user.id} удалил {deleted_count} трек-кодов.")
        await state.clear()  # Успешно, выходим

    except Exception as e:
        logger.error(f"Ошибка при удалении трек-кодов для админа {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при удалении трек-кодов. Попробуйте позже.", reply_markup=main_keyboard)
        await state.clear()


# ************************************************
# 3. ПОЛУЧЕНИЕ СПИСКА ТРЕК-КОДОВ (ОТЧЕТ)
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

    remove(excel_file_path)
    remove(text_file_path)


# ************************************************
# 4. ПОИСК ВЛАДЕЛЬЦА ТРЕК-КОДА (ОБНОВЛЕНО)
# ************************************************

@admin_tc_router.message(F.text == "Найти владельца трек-кода", IsAdmin(admin_ids))
async def find_owner_start(message: Message, state: FSMContext):
    """Начинает процесс поиска владельца по трек-коду."""
    await message.answer("Пожалуйста, отправьте трек-код для поиска владельца.",
                         reply_markup=cancel_keyboard)  # Добавляем клавиатуру отмены
    await state.set_state(TrackCodeStates.waiting_for_owner_search_code)


@admin_tc_router.message(TrackCodeStates.waiting_for_owner_search_code, F.text == "Отмена")
async def cancel_owner_search(message: Message, state: FSMContext):
    """Отменяет режим поиска владельца."""
    await message.answer("Поиск владельца отменен.", reply_markup=main_keyboard)
    await state.clear()


@admin_tc_router.message(TrackCodeStates.waiting_for_owner_search_code)
async def process_owner_search(message: Message, state: FSMContext):
    """Ищет владельца и статус по введенному трек-коду."""
    if not message.text:
        await message.answer("Пожалуйста, введите корректный трек-код.", reply_markup=cancel_keyboard)
        return  # Остаемся в состоянии

    track_code = message.text.strip()

    # get_track_code_info возвращает dict {'tg_id': 123, 'status': 'shipped', ...}
    track_info = await get_track_code_info(track_code)

    if track_info:
        user_tg_id = track_info.get('tg_id')
        status = track_info.get('status', 'неизвестен')

        if user_tg_id:
            # --- ЛОГИКА ДОБАВЛЕНИЯ КНОПОК РЕДАКТИРОВАНИЯ ---

            # 1. Получаем полный профиль пользователя по tg_id, чтобы найти внутренний ID
            user_data = await get_info_profile(user_tg_id)

            if user_data:
                internal_user_id = user_data.get('id')
                username = user_data.get('username')
                phone = user_data.get('phone')

                # 2. Отправляем основную информацию
                response = (
                    f"✅ <b>Информация о трек-коде:</b>\n"
                    f"Код: <code>{track_code}</code>\n"
                    f"Статус: <b>{status}</b>\n"
                    f"Владелец (TG ID): <code>{user_tg_id}</code>\n"
                    f"Внутренний ID: <code>FS{internal_user_id:04d}</code>\n"
                    f"Ссылка на чат: <a href='tg://user?id={user_tg_id}'>Написать пользователю</a>"
                )
                await message.answer(response)

                # 3. Генерируем клавиатуру редактирования
                edit_keyboard = get_admin_edit_user_keyboard(
                    internal_user_id=internal_user_id,
                    has_username=bool(username),
                    has_phone=bool(phone)
                )

                # 4. Отправляем второе сообщение с кнопками
                await message.answer(
                    "Вы можете <b>изменить данные</b> этого пользователя, "
                    "ввести следующий трек-код для поиска или нажать '<b>Отмена</b>'.",
                    reply_markup=edit_keyboard
                )

            else:
                # Странная ситуация: трек-код привязан к tg_id, которого нет в таблице users
                response = (
                    f"⚠️ <b>Информация о трек-коде:</b>\n"
                    f"Код: <code>{track_code}</code>\n"
                    f"Статус: <b>{status}</b>\n"
                    f"Владелец (TG ID): <code>{user_tg_id}</code>\n"
                    f"<b>Ошибка:</b> Не удалось найти профиль пользователя с этим TG ID в базе `users`."
                )
                await message.answer(response, reply_markup=cancel_keyboard)

        else:
            response = (
                f"⚠️ <b>Информация о трек-коде:</b>\n"
                f"Код: <code>{track_code}</code>\n"
                f"Статус: <b>{status}</b>\n"
                f"Владелец: <b>Не привязан к пользователю.</b>\n\n"
                f"Вы можете ввести следующий трек-код или нажать 'Отмена'."
            )
            await message.answer(response, reply_markup=cancel_keyboard)
    else:
        response = f"❌ Трек-код <code>{track_code}</code> не найден в базе данных."
        await message.answer(response, reply_markup=cancel_keyboard)

    # НЕ очищаем состояние, остаемся в режиме поиска

