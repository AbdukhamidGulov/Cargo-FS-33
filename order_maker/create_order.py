from asyncio import gather, get_running_loop, sleep
from os import path, makedirs, remove, listdir, rmdir
from logging import getLogger
from typing import List, Dict

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile

from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Font, Border, Side
from PIL import Image as PilImage

from keyboards import cancel_keyboard, main_keyboard, get_order_keyboard

order_router = Router()
logger = getLogger(__name__)

TEMP_FOLDER = "temp_orders"
IMAGE_SIZE = (120, 120)


class OrderItemsStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_quantity = State()
    waiting_for_track_code = State()
    waiting_for_link = State()
    confirm_next_step = State()


# --- СИНХРОННАЯ ФУНКЦИЯ (ВЫПОЛНЯЕТСЯ В ОТДЕЛЬНОМ ПОТОКЕ) ---
def generate_excel_sync(filename: str, form_title: str, client_data: Dict, items: List[Dict],
                        temp_paths: List[str]) -> None:
    """
    Создает Excel файл. Эта функция тяжелая (CPU/Disk I/O),
    поэтому она будет запущена через run_in_executor.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = form_title

    # 1. Шапка клиента
    headers_info = [
        ("B1", "ID Клиента:", client_data.get("id")),
        ("B2", "Имя клиента:", client_data.get("name")),
        ("B3", "Email:", client_data.get("email"))
    ]

    for cell, title, value in headers_info:
        ws[cell] = title
        ws[cell].font = Font(bold=True)
        # Соседняя ячейка (C1, C2, C3)
        val_cell = cell.replace("B", "C")
        ws[val_cell] = value

    # 2. Заголовки таблицы
    table_headers = ["№", "Фото", "Количество", "Трек-номер", "Ссылка/Описание"]
    start_row = 7

    ws.append([])
    ws.append([])
    ws.append(table_headers)  # 7-я строка

    # Настройка ширины
    col_widths = {'A': 5, 'B': 18, 'C': 15, 'D': 20, 'E': 40}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    # Стиль заголовков
    for cell in ws[start_row]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(bottom=Side(style='thin'))

    # 3. Заполнение товарами
    for i, item in enumerate(items, start=1):
        row = start_row + i

        # Номер
        ws.cell(row=row, column=1, value=i).alignment = Alignment(horizontal="center", vertical="center")

        # Фото
        photo_path = item.get('local_path')
        if photo_path and path.exists(photo_path):
            try:
                # Сжимаем фото для Excel
                resized_path = photo_path.replace("raw_", "res_")
                with PilImage.open(photo_path) as img:
                    img.thumbnail(IMAGE_SIZE)
                    img.save(resized_path)
                    temp_paths.append(resized_path)  # Добавляем в список на удаление

                img_obj = ExcelImage(resized_path)
                ws.add_image(img_obj, f"B{row}")
                ws.row_dimensions[row].height = 90
            except Exception as e:
                ws.cell(row=row, column=2, value="Error")
        else:
            ws.cell(row=row, column=2, value="Нет фото")

        # Данные
        ws.cell(row=row, column=3, value=item['quantity']).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=row, column=4, value=item['track']).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=row, column=5, value=item['link']).alignment = Alignment(vertical="center", wrap_text=True)

    wb.save(filename)


# --- ЛОГИКА БОТА ---

async def start_item_collection(message: Message, state: FSMContext):
    await message.answer(
        "✅ Данные подтверждены.\n\n"
        "📦 <b>Товар №1</b>\n📸 <b>Отправьте фото товара</b>:",
        reply_markup=cancel_keyboard
    )
    await state.set_state(OrderItemsStates.waiting_for_photo)


async def cancel_order_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_keyboard)


# --- ХЕНДЛЕРЫ ---

@order_router.message(OrderItemsStates.waiting_for_photo)
async def process_photo(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "отмена":
        await cancel_order_handler(message, state)
        return

    if not message.photo:
        await message.answer("Пожалуйста, отправьте <b>сжатое фото</b>, а не файл.")
        return

    # Берем последнее (самое качественное) фото
    await state.update_data(current_photo=message.photo[-1].file_id)
    await message.answer("🔢 <b>Введите количество</b> (например: <i>100 шт</i>):")
    await state.set_state(OrderItemsStates.waiting_for_quantity)


@order_router.message(OrderItemsStates.waiting_for_quantity, F.text)
async def process_quantity(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_order_handler(message, state)

    await state.update_data(current_quantity=message.text)
    await message.answer("🚚 <b>Введите трек-номер</b> (если нет, ставьте '-'):")
    await state.set_state(OrderItemsStates.waiting_for_track_code)


@order_router.message(OrderItemsStates.waiting_for_track_code, F.text)
async def process_track(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_order_handler(message, state)

    await state.update_data(current_track=message.text)
    await message.answer("🔗 <b>Ссылка на товар</b> или описание:")
    await state.set_state(OrderItemsStates.waiting_for_link)


@order_router.message(OrderItemsStates.waiting_for_link, F.text)
async def process_link(message: Message, state: FSMContext):
    if message.text.lower() == "отмена": return await cancel_order_handler(message, state)

    data = await state.get_data()
    items = data.get("items", [])

    new_item = {
        "photo_id": data.get("current_photo"),
        "quantity": data.get("current_quantity"),
        "track": data.get("current_track"),
        "link": message.text
    }
    items.append(new_item)
    await state.update_data(items=items)

    await message.answer(
        f"✅ Товар №{len(items)} сохранен!\nЧто дальше?",
        reply_markup=get_order_keyboard()
    )
    await state.set_state(OrderItemsStates.confirm_next_step)


@order_router.callback_query(OrderItemsStates.confirm_next_step, F.data == "order_add_next")
async def add_next_item(callback: CallbackQuery, state: FSMContext):
    if isinstance(callback.message, Message):
        try:
            await callback.message.delete()
        except Exception:
            pass

    data = await state.get_data()
    next_num = len(data.get("items", [])) + 1

    await callback.message.answer(
        f"📦 <b>Товар №{next_num}</b>\n📸 <b>Отправьте фото:</b>"
    )
    await state.set_state(OrderItemsStates.waiting_for_photo)


@order_router.callback_query(OrderItemsStates.confirm_next_step, F.data == "order_finish")
async def finish_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    items = data.get("items", [])

    if not items:
        await callback.message.answer("Список пуст.", reply_markup=main_keyboard)
        await state.clear()
        return

    await callback.message.edit_text("⏳ Скачиваю фото и формирую Excel...")

    if not path.exists(TEMP_FOLDER):
        makedirs(TEMP_FOLDER)

    client_id_str = data.get("client_excel_id", str(callback.from_user.id))
    excel_name = f"{TEMP_FOLDER}/order_{client_id_str}.xlsx"

    temp_files_to_clean = []

    try:
        # 1. Асинхронное скачивание фото (чтобы не морозить бота)
        download_tasks = []
        for idx, item in enumerate(items, 1):
            if item['photo_id']:
                file_path = f"{TEMP_FOLDER}/raw_{client_id_str}_{idx}.jpg"
                temp_files_to_clean.append(file_path)
                # Сохраняем путь, чтобы синхронная функция знала, где файл
                item['local_path'] = file_path

                # Добавляем задачу на скачивание
                file_info = await bot.get_file(item['photo_id'])
                download_tasks.append(bot.download_file(file_info.file_path, destination=file_path))

        if download_tasks:
            await gather(*download_tasks)

        # 2. Запуск тяжелой обработки в отдельном потоке (Executor)
        # Это предотвратит зависание бота при обработке картинок
        loop = get_running_loop()

        client_data = {
            "id": client_id_str,
            "name": data.get("client_name", "Unknown"),
            "email": data.get("client_email", "-")
        }

        await loop.run_in_executor(
            None,
            generate_excel_sync,
            excel_name,
            data.get("form_title", "Заказ"),
            client_data,
            items,
            temp_files_to_clean  # Передаем список, чтобы функция добавила туда res_ файлы
        )

        # 3. Отправка файла
        display_name = f"{data.get('form_title', 'Order')}_{client_id_str}.xlsx"
        file_doc = FSInputFile(excel_name, filename=display_name)

        await callback.message.answer_document(
            file_doc,
            caption=f"✅ <b>Готово!</b>\nКлиент: {client_id_str}\nПозиций: {len(items)}",
            reply_markup=main_keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при создании файла.")

    finally:
        # Очистка (удаляем файлы с диска)
        # Небольшая пауза, чтобы Telegram успел отправить файл
        await sleep(1)
        try:
            if path.exists(excel_name): remove(excel_name)
            for f in temp_files_to_clean:
                if path.exists(f): remove(f)
            # Удаляем папку если пуста
            if path.exists(TEMP_FOLDER) and not listdir(TEMP_FOLDER):
                rmdir(TEMP_FOLDER)
        except Exception as e:
            logger.error(f"Ошибка очистки: {e}")

        await state.clear()
