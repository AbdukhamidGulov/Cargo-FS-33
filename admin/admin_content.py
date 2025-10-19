from logging import getLogger

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.info_content import get_info_content, update_info_content
from filters_and_config import IsAdmin, admin_ids
from keyboards import create_inline_button, create_inline_keyboard, main_keyboard, cancel_keyboard

admin_content_router = Router()
logger = getLogger(__name__)


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
    "document": ["order_form", "prices_document", "tariffs_document"]
}


# Старт процесса изменения контента
@admin_content_router.message(F.text == "Изменить данные", IsAdmin(admin_ids))
async def start_edit_content(message: Message, state: FSMContext):
    """Показывает список ключей для изменения, отсортированный по алфавиту."""
    all_keys = []
    for type_keys in CONTENT_TYPES.values():
        all_keys.extend(type_keys)

    buttons = [[create_inline_button(key, callback_data=f"edit_{key}")] for key in sorted(all_keys)]
    buttons.append([create_inline_button("Отмена", callback_data="cancel_edit")]) # Инлайн-кнопка отмены
    keyboard = create_inline_keyboard(buttons)

    await message.answer("Выберите, что хотите изменить:", reply_markup=keyboard)
    await state.set_state(ContentEdit.select_key)


# Обработка выбора ключа
@admin_content_router.callback_query(ContentEdit.select_key, F.data.startswith("edit_"), IsAdmin(admin_ids))
async def select_key(callback: CallbackQuery, state: FSMContext):
    """Запрашивает новое значение для выбранного ключа и показывает текущее."""
    key = callback.data.replace("edit_", "")
    await state.update_data(selected_key=key)

    content_type = "text"
    for type_, keys in CONTENT_TYPES.items():
        if key in keys:
            content_type = type_
            break

    current_value = await get_info_content(key)

    if current_value:
        try:
            if content_type == "text":
                await callback.message.answer(f"Текущий текст для <code>{key}</code>:\n")
                await callback.message.answer(current_value)
                await callback.message.answer("Отправьте новый текст.\n")
            elif content_type == "photo":
                await callback.message.answer_photo(photo=current_value, caption=f"Текущее фото для <code>{key}</code>.\n\nОтправьте новое фото.")
            elif content_type == "video":
                await callback.message.answer_video(video=current_value, caption=f"Текущее видео для <code>{key}</code>.\n\nОтправьте новое видео.")
            elif content_type == "document":
                await callback.message.answer_document(document=current_value, caption=f"Текущий документ для <code>{key}</code>.\n\nОтправьте новый документ.")
            else:
                await callback.message.answer(f"Текущее значение для <code>{key}</code>: (неизвестный тип контента).\n\nОтправьте новое значение.")
        except Exception as e:
            logger.error(f"Ошибка при показе текущего контента для {key}: {e}")
            await callback.message.answer(f"Не удалось показать текущий контент для <code>{key}</code>. Возможно, он отсутствует или поврежден. Пожалуйста, отправьте новое значение.")
    else:
        await callback.message.answer(f"Для <code>{key}</code> пока нет сохраненного контента. Пожалуйста, отправьте новое значение.")

    await callback.message.answer("Для отмены нажмите кнопку 'Отмена'.", reply_markup=cancel_keyboard)
    await state.set_state(ContentEdit.input_content)
    await callback.answer()


# Обработка текста
@admin_content_router.message(ContentEdit.input_content, F.text, IsAdmin(admin_ids))
async def process_text(message: Message, state: FSMContext):
    """Обновляет текстовое значение с сохранением HTML-разметки."""
    if message.text.lower() == "отмена":
        await cancel_edit_process(message, state)
        return

    data = await state.get_data()
    key = data.get("selected_key")
    if key in CONTENT_TYPES["text"]:
        new_text = message.html_text
        await update_info_content(key, new_text)
        await message.answer(f"Текст для <code>{key}</code> обновлён.", reply_markup=main_keyboard)
    else:
        await message.answer("Ожидался текст, но выбранный ключ не текстовый. Пожалуйста, отправьте текст.", reply_markup=cancel_keyboard)
    await state.clear()


# Обработка фото
@admin_content_router.message(ContentEdit.input_content, F.photo, IsAdmin(admin_ids))
async def process_photo(message: Message, state: FSMContext):
    """Обновляет токен фото в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    if key in CONTENT_TYPES["photo"]:
        photo_token = message.photo[-1].file_id
        await update_info_content(key, photo_token)
        await message.answer(f"Фото для <code>{key}</code> обновлено.", reply_markup=main_keyboard)
    else:
        await message.answer("Ожидалось фото, но выбранный ключ не соответствует типу. Пожалуйста, отправьте фото.", reply_markup=cancel_keyboard)
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
        await message.answer("Ожидалось видео, но выбранный ключ не соответствует типу. Пожалуйста, отправьте видео.", reply_markup=cancel_keyboard)
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
        await message.answer("Ожидался документ, но выбранный ключ не соответствует типу. Пожалуйста, отправьте документ.", reply_markup=cancel_keyboard)
    await state.clear()


# Обработка отмены (инлайн-кнопка)
@admin_content_router.callback_query(F.data == "cancel_edit", IsAdmin(admin_ids))
async def cancel_edit_inline(callback: CallbackQuery, state: FSMContext):
    """Отменяет процесс редактирования через инлайн-кнопку."""
    await callback.message.delete()
    await cancel_edit_process(callback.message, state)
    await callback.answer()


# Новый хендлер для текстовой кнопки "Отмена"
@admin_content_router.message(F.text == "отмена", IsAdmin(admin_ids))
async def cancel_edit_text_button(message: Message, state: FSMContext):
    """Отменяет процесс редактирования через текстовую кнопку."""
    await cancel_edit_process(message, state)


# Вспомогательная функция для отмены, чтобы избежать дублирования кода
async def cancel_edit_process(message: Message, state: FSMContext):
    """Общая логика отмены редактирования контента."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
    else:
        await message.answer("Вы уже находитесь в главном меню.", reply_markup=main_keyboard)


# Обработка некорректного ввода
@admin_content_router.message(ContentEdit.input_content, IsAdmin(admin_ids))
async def invalid_input(message: Message, state: FSMContext):
    """Обрабатывает некорректный ввод."""
    # Если это не кнопка "Отмена" (уже обработанная выше)
    if message.text.lower() != "отмена":
        data = await state.get_data()
        key = data.get("selected_key")
        content_type = "text"
        for type_, keys in CONTENT_TYPES.items():
            if key in keys:
                content_type = type_
                break
        await message.answer(f"Ожидался {content_type}. Пожалуйста, отправьте корректный формат для '{key}'.", reply_markup=cancel_keyboard)
