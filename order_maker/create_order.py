from os import path, makedirs, remove, listdir, rmdir
from logging import getLogger

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile

# Работа с Excel и изображениями
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Font, Border, Side
from PIL import Image as PilImage

from keyboards import cancel_keyboard, main_keyboard, get_order_keyboard

order_router = Router()
logger = getLogger(__name__)

# Константы
TEMP_FOLDER = "temp_orders"
IMAGE_SIZE = (120, 120)


class OrderItemsStates(StatesGroup):
    """Состояния для добавления товаров в заказ."""
    waiting_for_photo = State()
    waiting_for_quantity = State()
    waiting_for_track_code = State()
    waiting_for_link = State()
    confirm_next_step = State()


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def ensure_temp_folder():
    """Создает папку для временных файлов, если её нет."""
    if not path.exists(TEMP_FOLDER):
        makedirs(TEMP_FOLDER)


async def cancel_order(message: Message, state: FSMContext):
    """Сброс состояния и отмена заказа."""
    await message.answer("Действие отменено.", reply_markup=main_keyboard)
    await state.clear()


# --- ПУБЛИЧНАЯ ТОЧКА ВХОДА (вызывается из user_collector.py) ---

async def start_item_collection(message: Message, state: FSMContext):
    """
    Инициирует процесс добавления первого товара.
    Вызывается после успешного сбора данных пользователя в user_collector.py.
    """
    await message.answer(
        "✅ Данные профиля подтверждены.\n\n"
        "📦 <b>Товар №1</b>\n"
        "📸 <b>Отправьте фотографию товара</b>:",
        reply_markup=cancel_keyboard
    )
    await state.set_state(OrderItemsStates.waiting_for_photo)


# --- ХЕНДЛЕРЫ FSM: ДОБАВЛЕНИЕ ТОВАРОВ ---

@order_router.message(OrderItemsStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Сохраняет file_id фото и запрашивает количество."""
    photo_id = message.photo[-1].file_id
    await state.update_data(current_photo=photo_id)

    await message.answer(
        "✅ Фото принято.\n\n"
        "🔢 <b>Введите количество</b> (например: <i>100 шт</i>):"
    )
    await state.set_state(OrderItemsStates.waiting_for_quantity)


@order_router.message(OrderItemsStates.waiting_for_photo)
async def process_photo_error(message: Message, state: FSMContext):
    """Обработка не-фото сообщений."""
    if message.text and message.text.lower() == "отмена":
        await cancel_order(message, state)
        return
    await message.answer("Пожалуйста, отправьте именно <b>фотографию</b> (сжатое изображение), а не файл.")


@order_router.message(OrderItemsStates.waiting_for_quantity, F.text)
async def process_quantity(message: Message, state: FSMContext):
    """Сохраняет количество и запрашивает трек-код."""
    if message.text.lower() == "отмена":
        await cancel_order(message, state)
        return

    await state.update_data(current_quantity=message.text)

    await message.answer(
        "🚚 <b>Введите трек-номер</b> посылки (по Китаю):\n"
        "<i>Если нет, поставьте прочерк (-)</i>"
    )
    await state.set_state(OrderItemsStates.waiting_for_track_code)


@order_router.message(OrderItemsStates.waiting_for_track_code, F.text)
async def process_track_code(message: Message, state: FSMContext):
    """Сохраняет трек-код и запрашивает ссылку."""
    if message.text.lower() == "отмена":
        await cancel_order(message, state)
        return

    await state.update_data(current_track=message.text)

    await message.answer(
        "🔗 <b>Отправьте ссылку на товар</b> (или краткое описание):"
    )
    await state.set_state(OrderItemsStates.waiting_for_link)


@order_router.message(OrderItemsStates.waiting_for_link, F.text)
async def process_link(message: Message, state: FSMContext):
    """Сохраняет ссылку, добавляет товар в список и предлагает следующий шаг."""
    if message.text.lower() == "отмена":
        await cancel_order(message, state)
        return

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
        f"✅ Товар №{len(items)} сохранен!\n\n"
        "Что делаем дальше?",
        reply_markup=get_order_keyboard()
    )
    await state.set_state(OrderItemsStates.confirm_next_step)


@order_router.callback_query(OrderItemsStates.confirm_next_step, F.data == "order_add_next")
async def add_next_item(callback: CallbackQuery, state: FSMContext):
    """Переход к добавлению следующего товара."""
    await callback.message.delete()
    data = await state.get_data()
    next_num = len(data.get("items", [])) + 1

    await callback.message.answer(f"📦 <b>Товар №{next_num}</b>\n📸 <b>Отправьте фотографию:</b>")
    await state.set_state(OrderItemsStates.waiting_for_photo)


@order_router.callback_query(OrderItemsStates.confirm_next_step, F.data == "order_finish")
async def finish_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Формирование Excel с данными клиента и списком товаров."""
    await callback.message.edit_text("⏳ Формирую файл заказа, это может занять время...")

    data = await state.get_data()
    items = data.get("items", [])

    # Данные клиента, собранные в user_collector (должны быть в FSMContext)
    client_name = data.get("client_name", "Не указано")
    client_email = data.get("client_email", "Не указано")

    # Идентификатор клиента для имени файла (FS0335). Берется из FSM, куда записывается
    # в user_collector (ID пользователя бота, например FS0335)
    client_excel_id = data.get("client_excel_id", str(callback.from_user.id))
    form_title = data.get("form_title", "Заказ")

    if not items:
        await callback.message.answer("Список пуст.", reply_markup=main_keyboard)
        await state.clear()
        return

    ensure_temp_folder()
    temp_files = []

    # Имя файла включает FS ID или TG ID
    excel_filename = f"{TEMP_FOLDER}/order_{client_excel_id}.xlsx"

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = form_title

        # --- Шапка с данными клиента ---
        # Название в B, Значение в C

        # 1. ID Клиента (B1, C1)
        ws["B1"] = "ID Клиента:"
        ws["C1"] = client_excel_id

        # 2. Имя клиента (B2, C2)
        ws["B2"] = "Имя клиента:"
        ws["C2"] = client_name

        # 3. Email (B3, C3)
        ws["B3"] = "Email:"
        ws["C3"] = client_email

        # Стиль для заголовков (B1:B3)
        for row in range(1, 4):
            ws.cell(row=row, column=2).font = Font(bold=True)  # B1, B2, B3

        # --- Заголовки таблицы товаров ---
        headers = ["№", "Фото", "Количество", "Трек-номер", "Ссылка/Описание"]
        # Сдвигаем вниз до 7-й строки
        header_row_idx = 7
        ws.append([])  # Пустая строка
        ws.append([])  # Пустая строка
        ws.append(headers)

        # Настройка ширины колонок
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 40

        # Стиль заголовков таблицы
        for cell in ws[header_row_idx]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = Border(bottom=Side(style='thin'))

        # --- Заполнение данными ---
        for index, item in enumerate(items, start=1):
            row_num = header_row_idx + index

            # 1. Номер (A)
            cell_num = ws.cell(row=row_num, column=1, value=index)
            cell_num.alignment = Alignment(vertical="center", horizontal="center")

            # 2. ФОТО (B)
            photo_id = item['photo_id']
            if photo_id:
                try:
                    file = await bot.get_file(photo_id)
                    raw_photo_path = f"{TEMP_FOLDER}/raw_{index}_{photo_id}.jpg"
                    resized_photo_path = f"{TEMP_FOLDER}/res_{index}_{photo_id}.jpg"

                    await bot.download_file(file.file_path, destination=raw_photo_path)
                    temp_files.append(raw_photo_path)

                    with PilImage.open(raw_photo_path) as img:
                        img.thumbnail(IMAGE_SIZE)
                        img.save(resized_photo_path)
                        temp_files.append(resized_photo_path)

                    excel_img = ExcelImage(resized_photo_path)

                    # (Код для центрирования удален, как и просили)

                    anchor = f"B{row_num}"  # Колонка B для фото
                    ws.add_image(excel_img, anchor)
                    ws.row_dimensions[row_num].height = 90

                except Exception as e:
                    logger.error(f"Ошибка обработки фото (товар {index}): {e}")
                    ws.cell(row=row_num, column=2, value="Ошибка фото")
            else:
                ws.cell(row=row_num, column=2, value="Нет фото")

            # Остальные колонки
            # Количество (C)
            ws.cell(row=row_num, column=3, value=item['quantity']).alignment = Alignment(vertical="center",
                                                                                         horizontal="center")
            # Трек-номер (D)
            ws.cell(row=row_num, column=4, value=item['track']).alignment = Alignment(vertical="center",
                                                                                      horizontal="center")
            # Ссылка (E)
            ws.cell(row=row_num, column=5, value=item['link']).alignment = Alignment(vertical="center", wrap_text=True)

        wb.save(excel_filename)

        # Отправка
        # Имя файла для отображения включает FS ID
        display_filename = f"{form_title}_{client_excel_id}.xlsx"
        file_doc = FSInputFile(excel_filename, filename=display_filename)

        await callback.message.answer_document(
            file_doc,
            caption=f"✅ <b>Ваш документ ({form_title}) готов!</b>\n"
                    f"Код клиента: <b>{client_excel_id}</b>\n"
                    f"Всего позиций: {len(items)}\n"
                    f"Отправьте этот файл менеджеру.",
            reply_markup=main_keyboard
        )

    except Exception as e:
        logger.error(f"Глобальная ошибка создания Excel: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при создании файла.", reply_markup=main_keyboard)

    finally:
        # Очистка
        try:
            for f in temp_files:
                if path.exists(f): remove(f)
            if path.exists(excel_filename): remove(excel_filename)
            if path.exists(TEMP_FOLDER) and not listdir(TEMP_FOLDER):
                rmdir(TEMP_FOLDER)
        except Exception as e:
            logger.error(f"Ошибка очистки временных файлов: {e}")

    await state.clear()