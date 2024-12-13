from os import remove
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook

from database import (get_track_codes_list, drop_users_table, create_users_table, drop_track_numbers_table,
                      create_track_codes_table, get_users_tg_info, get_user_by_id, add_or_update_track_codes_list)
from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard

admin = Router()


@admin.message(F.text == "Админ", IsAdmin(admin_ids))
@admin.message(Command(commands=['admin']), IsAdmin(admin_ids))
async def admin_command(message: Message):
    await message.answer('Выберите команду', reply_markup=admin_keyboard)


@admin.message(Command(commands=['admin']))
async def admin_command(message: Message, bot: Bot):
    await message.answer('Вы не являетесь админом')
    await bot.send_message(admin_ids[0], text=f"Пользователь {message.from_user.username} "
                                              f"c id {message.from_user.id} нажал на команду <b>admin</b>")
    print(message.from_user.id)


# Искать информацию по ID
class SearchUserStates(StatesGroup):
    waiting_for_user_id = State()

@admin.message(F.text == "Искать информацию по ID")
async def search_by_id(message: Message, state: FSMContext):
    await message.answer("Введите ID пользователя (например, FS0001 или просто 1):")
    await state.set_state(SearchUserStates.waiting_for_user_id)

@admin.message(SearchUserStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    user_id = message.text.strip()
    user_data = await get_user_by_id(user_id)

    if not user_data:
        await message.answer("Пользователь с таким ID не найден.")
        await state.clear()
        return

    no = "<i>Не заполнено</i>"
    await message.answer(
        f"ID: <code>FS{user_data['id']:04d}</code>\n"
        f"Имя: {user_data['name'] or no}\n"
        f"Username: @{user_data['username'] or no}\n"
        f"Номер телефона: {user_data['phone'] or no}\n"
    )
    await state.clear()


# Добавить трек-номера
class TrackCodeStates(StatesGroup):
    waiting_for_codes = State()

async def handle_track_codes(message: Message, state: FSMContext, status: str, bot: Bot):
    track_codes = []

    if message.text:
        track_codes = list(filter(None, map(str.strip, message.text.split())))
    elif message.document:
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        file_content = await bot.download_file(file_path)
        content = file_content.read().decode('utf-8')
        track_codes = list(filter(None, map(str.strip, content.splitlines())))

    if not track_codes:
        await message.answer("Не удалось получить трек-коды. Убедитесь, что отправили текст или текстовый файл с кодами.")
        return

    action = "добавлено" if status == "in_stock" else "обновлено"
    status_text = "На складе" if status == "in_stock" else "Отправлен"

    try:
        await add_or_update_track_codes_list(track_codes, status, bot, message)
        await message.answer(
            f"Успешно {action} {len(track_codes)} трек-кодов в базу данных со статусом '{status_text}'.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при {action} трек-кодов: {e}")
    finally:
        await state.clear()

@admin.message(F.text == "❕Добавить пребывшие на склад трек-коды", IsAdmin(admin_ids))
async def add_track_codes(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте список трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_codes)
    await state.update_data(status="in_stock")

@admin.message(F.text == "Добавить отправленные трек-коды", IsAdmin(admin_ids))
async def add_shipped_track_codes(message: Message, state: FSMContext):
    await message.answer("Отправьте список отправленных трек-кодов или загрузите файл (формат .txt):\n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_codes)
    await state.update_data(status="shipped")

@admin.message(TrackCodeStates.waiting_for_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    status = data.get("status")
    await handle_track_codes(message, state, status, bot)


# Получение списка трек-кодов
@admin.message(F.text == "️Список трек-кодов",  IsAdmin(admin_ids))
async def track_codes_list(message: Message):
    await message.delete()
    track_codes = await get_track_codes_list()  # [Row(id, track_code, status, tg_id)]
    users = await get_users_tg_info()  # {tg_id: username}

    # Создаем Excel файл
    excel_file_path = "track_codes.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Track Codes"

    # Устанавливаем заголовки
    headers = ["ID", "Track Code", "Status", "User"]
    sheet.append(headers)

    for col in sheet.iter_cols(min_row=1, max_row=1, min_col=1, max_col=len(headers)):
        for cell in col:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Добавляем данные в Excel
    for row in track_codes:
        user = f"t.me/{users.get(row["tg_id"], "")}" if row["tg_id"] else ""
        sheet.append([row["id"], row["track_code"], row["status"], user])

    # Сохраняем Excel файл
    workbook.save(excel_file_path)


    # Создаем текстовый документ
    text_file_path = "track_codes.txt"
    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write("Список трек-кодов\n")
        text_file.write("=" * 40 + "\n")
        for row in track_codes:
            user = users.get(row["tg_id"], "—") if row["tg_id"] else "—"
            text_file.write(
                f"{row['id']:03d}. Track Code: {row['track_code']}, Status: {row['status']}, User: t.me/{user}\n"
            )

    # Создаём объекты InputFile
    excel_file_input = FSInputFile(excel_file_path)  # Указываем путь к Excel-файлу
    text_file_input = FSInputFile(text_file_path)  # Указываем путь к текстовому файлу

    # Отправляем файлы
    await message.answer_document(excel_file_input)
    await message.answer_document(text_file_input)

    # Удаляем файлы после отправки
    remove(excel_file_path)
    remove(text_file_path)


@admin.message(F.text == "️Пересоздать БД пользователей", IsAdmin(admin_ids))
async def recreat_db(message: Message):
    await drop_users_table()
    await create_users_table()
    await message.answer('База данных пользователей успешно пересоздана!')


@admin.message(F.text  == "️Пересоздать БД трек-номеров", IsAdmin(admin_ids))
async def recreate_tc(message: Message):
    await drop_track_numbers_table()
    await create_track_codes_table()
    await message.answer('База данных Трек-номеров успешно пересоздана!')


# ФУНКЦИИ ДЛЯ УЛАВЛОВАНИЯ ТОКЕНОВ ФАЙЛОВ
@admin.message(F.photo, IsAdmin(admin_ids))
async def get_photo_id(message: Message):
    print_token_photo = message.photo[0].file_id
    await message.answer(f"<b>Токен скинутого фото:</b>\n<code>{print_token_photo}</code>")
    print(print_token_photo)

@admin.message(F.video, IsAdmin(admin_ids))
async def get_video_id(message: Message):
    print_token_video = message.video.file_id
    await message.answer(f"<b>Токен скинутого видео:</b>\n<code>{print_token_video}</code>")
    print(print_token_video)

@admin.message(F.document)
async def get_document_id(message: Message):
    print_token_document = message.document.file_id
    await message.answer(f"<b>Токен скинутого документа:</b>\n<code>{print_token_document}</code>")
    print(print_token_document)
