from os import remove
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook

from database import get_track_codes_list, drop_users_table, create_users_table, \
    drop_track_numbers_table, create_track_codes_table, add_track_codes_list, get_users_tg_info
from filters_and_config import IsAdmin, admin_ids
from keyboards import admin_keyboard

admin = Router()


@admin.message(F.text == "Админ", IsAdmin(admin_ids))
@admin.message(Command(commands=['admin']), IsAdmin(admin_ids))
async def admin_command(message: Message):
    await message.answer('Выберите команду', reply_markup=admin_keyboard)


@admin.message(Command(commands=['admin']))
async def admin_command(message: Message, bot: Bot):
    await message.answer('Вы не явяетесь админом')
    await bot.send_message(admin_ids[0], text=f"Пользоватеь {message.from_user.username} "
                                              f"c id {message.from_user.id} нажал на команду <b>admin</b>")
    print(message.from_user.id)


@admin.message(F.text == "️Пересоздать БД пользователей", IsAdmin(admin_ids))
async def recreat_db(message: Message):
    await drop_users_table()
    await create_users_table()
    await message.answer('База данных пользователей успешно песоздана!')


@admin.message(F.text  == "️Пересоздать БД трек-номеров", IsAdmin(admin_ids))
async def recreate_tc(message: Message):
    await drop_track_numbers_table()
    await create_track_codes_table()
    await message.answer('База данных Трек-номеров успешно песоздана!')


@admin.message(F.photo, IsAdmin(admin_ids))
async def photo(message: Message):
    await message.answer(print_token_photo := message.photo[0].file_id)
    print(print_token_photo)



# Добавление трек-кодов
class TrackCodeStates(StatesGroup):
    waiting_for_track_codes = State()


@admin.message(F.text == "️Добавить трек-коды", IsAdmin(admin_ids))
async def add_track_codes(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте список трек-кодов \n"
                         "<i>(каждый трек-код с новой строки или через пробел)</i>.")
    await state.set_state(TrackCodeStates.waiting_for_track_codes)

@admin.message(TrackCodeStates.waiting_for_track_codes)
async def process_track_codes(message: Message, state: FSMContext):
    track_codes = list(filter(None, map(str.strip, message.text.split())))
    if not track_codes:
        await message.answer("Список трек-кодов пуст. Пожалуйста, отправьте данные снова.")
        return

    # Добавляем трек-коды в базу данных
    try:
        await add_track_codes_list(track_codes)
        await message.answer(f"Успешно добавлено {len(track_codes)} трек-кодов в базу данных со статусом 'На скаде'.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении трек-кодов: {e}")

    await state.clear()



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
