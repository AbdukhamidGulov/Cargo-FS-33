from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from database.info_content import InfoContent, get_info_content, update_info_content, async_session
from filters_and_config import IsAdmin, admin_ids
from keyboards import create_inline_button, create_inline_keyboard, main_keyboard

admin_content_router = Router()


# Определяем состояния FSM
class ContentEdit(StatesGroup):
    select_key = State()  # Выбор ключа для редактирования
    input_content = State()  # Ввод нового значения


# Классификация ключей по типам контента
CONTENT_TYPES = {
    "text": [
        "warehouse_address", "blank_info", "tariffs", "goods_check", "consolidation",
        "forbidden_goods", "packing", "prices"
    ],
    "photo": [
        "main_menu_photo", "sample_1688", "sample_Taobao", "sample_Pinduoduo", "sample_Poizon",
        "track_number_info_photo1_1688", "track_number_info_photo2_1688",
        "track_number_info_photo1_Taobao", "track_number_info_photo2_Taobao",
        "track_number_info_photo1_Pinduoduo", "track_number_info_photo2_Pinduoduo",
        "track_number_info_photo1_Poizon", "track_number_info_photo2_Poizon",
        "calculate_volume_photo1", "calculate_volume_photo5", "consolidation_photo",
        "packing_photo", "goods_check_photo1", "goods_check_photo2", "goods_check_photo3"
    ],
    "video": ["goods_check_video1", "goods_check_video2"],
    "document": ["order_form", "prices_document"]
    }


# Старт процесса изменения контента
@admin_content_router.message(F.text == "Изменить данные", IsAdmin(admin_ids))
async def start_edit_content(message: Message, state: FSMContext):
    """Показывает список ключей для изменения."""
    async with async_session() as session:
        result = await session.execute(select(InfoContent))
        contents = result.scalars().all()
        if not contents:
            await message.answer("В таблице info_content нет данных.")
            return

        buttons = [[create_inline_button(content.key, callback_data=f"edit_{content.key}")] for content in contents]
        buttons.append([create_inline_button("Отмена", callback_data="cancel_edit")])
        keyboard = create_inline_keyboard(buttons)

        await message.answer("Выберите, что хотите изменить:", reply_markup=keyboard)
        await state.set_state(ContentEdit.select_key)


# Обработка выбора ключа
@admin_content_router.callback_query(ContentEdit.select_key, F.data.startswith("edit_"), IsAdmin(admin_ids))
async def select_key(callback: CallbackQuery, state: FSMContext):
    """Запрашивает новое значение для выбранного ключа."""
    key = callback.data.replace("edit_", "")
    await state.update_data(selected_key=key)

    # Определяем тип контента
    content_type = "text"  # По умолчанию текст
    for type_, keys in CONTENT_TYPES.items():
        if key in keys:
            content_type = type_
            break

    # Показываем текущее значение
    current_value = await get_info_content(key)
    if current_value:
        await callback.message.answer(f"Текущее значение '{key}':\n{current_value}", parse_mode="HTML" if content_type == "text" else None)

    # Запрос нового значения
    prompts = {
        "text": "Отправьте новый текст",
        "photo": "Отправьте новое фото.",
        "video": "Отправьте новое видео.",
        "document": "Отправьте новый документ."
    }
    await callback.message.answer(prompts[content_type])
    await state.set_state(ContentEdit.input_content)
    await callback.answer()


# Обработка текста
@admin_content_router.message(ContentEdit.input_content, F.text, IsAdmin(admin_ids))
async def process_text(message: Message, state: FSMContext):
    """Обновляет текстовое значение с сохранением HTML-разметки."""
    data = await state.get_data()
    key = data.get("selected_key")
    if key in CONTENT_TYPES["text"]:
        new_text = message.html_text  # Сохраняем текст с HTML-разметкой
        await update_info_content(key, new_text)
        await message.answer(f"Текст для <code>{key}</code> обновлён.", reply_markup=main_keyboard, parse_mode="HTML")
    else:
        await message.answer("Ожидался текст, но ключ не текстовый.")
    await state.clear()


# Обработка фото
@admin_content_router.message(ContentEdit.input_content, F.photo, IsAdmin(admin_ids))
async def process_photo(message: Message, state: FSMContext):
    """Обновляет токен фото в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    if key in CONTENT_TYPES["photo"]:
        photo_token = message.photo[-1].file_id  # Берем фото максимального качества
        await update_info_content(key, photo_token)
        await message.answer(f"Фото для <code>{key}</code> обновлено.", reply_markup=main_keyboard)
    else:
        await message.answer("Ожидалось фото, но ключ не соответствует типу.")
    await state.clear()


# Обработка видео
@admin_content_router.message(ContentEdit.input_content, F.video, IsAdmin(admin_ids))
async def process_video(message: Message, state: FSMContext):
    """Обновляет токен видео в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    if key in CONTENT_TYPES["video"]:
        video_token = message.video.file_id
        await update_info_content(key, video_token)
        await message.answer(f"Видео для <code>{key}</code> обновлено.", reply_markup=main_keyboard)
    else:
        await message.answer("Ожидалось видео, но ключ не соответствует типу.")
    await state.clear()


# Обработка документа
@admin_content_router.message(ContentEdit.input_content, F.document, IsAdmin(admin_ids))
async def process_document(message: Message, state: FSMContext):
    """Обновляет токен документа в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    if key in CONTENT_TYPES["document"]:
        document_token = message.document.file_id
        await update_info_content(key, document_token)
        await message.answer(f"Документ для <code>{key}</code> обновлён.", reply_markup=main_keyboard)
    else:
        await message.answer("Ожидался документ, но ключ не соответствует типу.")
    await state.clear()


# Обработка отмены
@admin_content_router.callback_query(F.data == "cancel_edit", IsAdmin(admin_ids))
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    """Отменяет процесс редактирования."""
    await callback.message.delete()
    await callback.message.answer("Редактирование отменено.", reply_markup=main_keyboard)
    await state.clear()

# Обработка некорректного ввода
@admin_content_router.message(ContentEdit.input_content, IsAdmin(admin_ids))
async def invalid_input(message: Message, state: FSMContext):
    """Обрабатывает некорректный ввод."""
    data = await state.get_data()
    key = data.get("selected_key")
    content_type = "text"
    for type_, keys in CONTENT_TYPES.items():
        if key in keys:
            content_type = type_
            break
    await message.answer(f"Ожидалось {content_type}, попробуйте снова.")
