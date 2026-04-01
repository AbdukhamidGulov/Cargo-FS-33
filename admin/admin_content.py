from logging import getLogger

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.db_info_content import get_info_content, update_info_content
from filters_and_config import IsAdmin, admin_ids
from keyboards.common_keyboards import create_inline_button, create_inline_keyboard
from keyboards.user_keyboards import cancel_keyboard, main_keyboard

admin_content_router = Router()
logger = getLogger(__name__)


class ContentEdit(StatesGroup):
    select_category = State()
    select_key = State()
    input_content = State()


# Классификация ключей по типам контента
CONTENT_TYPES = {
    "text": [
        "warehouse_address", "blank_text", "tariffs_text", "goods_check_text", "consolidation_text",
        "forbidden_goods", "packing_text", "prices_text", "customs_form_text", "insurance_info"
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
    "document": ["order_form", "prices_document", "tariffs_document", "customs_form_document"]
}


# 1. Названия категорий
CATEGORY_NAMES = {
    "text": "📝 Текстовые блоки",
    "photo": "🖼️ Фотографии",
    "video": "🎬 Видео",
    "document": "📄 Документы"
}

# 2. Названия самих ключей (для удобства админа)
KEY_NAMES = {
    # Текст
    "warehouse_address": "Адрес склада",
    "blank_text": "Текст 'Бланк Заказа'",
    "tariffs_text": "Текст 'Тарифы'",
    "goods_check_text": "Текст 'Проверка товаров'",
    "consolidation_text": "Текст 'Консолидация'",
    "forbidden_goods": "Запрещённые товары",
    "packing_text": "Текст 'Упаковка'",
    "prices_text": "Текст 'Цены'",
    "customs_form_text": "Текст 'Бланк Таможни'",
    "insurance_info": "Текст 'Страхование'",

    # Фото
    "main_menu_photo": "Фото 'Главное меню'",
    "sample_1688": "Фото 'Образец 1688'",
    "sample_Taobao": "Фото 'Образец Taobao'",
    "sample_Pinduoduo": "Фото 'Образец Pinduoduo'",
    "sample_Poizon": "Фото 'Образец Poizon'",
    "track_number_info_photo1_1688": "Фото 'Трек-код 1 (1688)'",
    "track_number_info_photo2_1688": "Фото 'Трек-код 2 (1688)'",
    "track_number_info_photo1_Taobao": "Фото 'Трек-код 1 (Taobao)'",
    "track_number_info_photo2_Taobao": "Фото 'Трек-код 2 (Taobao)'",
    "track_number_info_photo1_Pinduoduo": "Фото 'Трек-код 1 (Pinduoduo)'",
    "track_number_info_photo2_Pinduoduo": "Фото 'Трек-код 2 (Pinduoduo)'",
    "track_number_info_photo1_Poizon": "Фото 'Трек-код 1 (Poizon)'",
    "track_number_info_photo2_Poizon": "Фото 'Трек-код 2 (Poizon)'",
    "calculate_volume_photo1": "Фото 'Калькулятор основной'",
    "calculate_volume_photo5": "Фото 'Калькулятор финалный'",
    "consolidation_photo": "Фото 'Консолидация'",
    "packing_photo": "Фото 'Упаковка'",
    "goods_check_photo1": "Фото 'Проверка (1)'",
    "goods_check_photo2": "Фото 'Проверка (2)'",
    "goods_check_photo3": "Фото 'Проверка (3)'",

    # Видео
    "goods_check_video1": "Видео 'Проверка (1)'",
    "goods_check_video2": "Видео 'Проверка (2)'",

    # Документы
    "order_form": "Файл 'Бланк Заказа'",
    "prices_document": "Файл 'Цены'",
    "tariffs_document": "Файл 'Тарифы'",
    "customs_form_document": "Файл 'Бланк Таможни'"
}


# --- FSM FLOW ---

# Шаг 1: Показать Категории
@admin_content_router.message(F.text == "Изменить данные", IsAdmin(admin_ids))
async def start_edit_content(message: Message, state: FSMContext):
    """
    Показывает администратору выбор КАТЕГОРИИ контента.
    """
    buttons = []
    # Создаем кнопки для каждой категории
    for category_key, category_name in CATEGORY_NAMES.items():
        buttons.append([
            create_inline_button(
                text=category_name,
                callback_data=f"select_category_{category_key}"
            )
        ])

    buttons.append([create_inline_button("Отмена", callback_data="cancel_edit")])
    keyboard = create_inline_keyboard(buttons)

    await message.answer("Выберите категорию контента, которую хотите изменить:", reply_markup=keyboard)
    await state.set_state(ContentEdit.select_category)


# Шаг 2: Показать Ключи в Категории
@admin_content_router.callback_query(ContentEdit.select_category, F.data.startswith("select_category_"),
                                     IsAdmin(admin_ids))
async def handle_category_selection(callback: CallbackQuery, state: FSMContext):
    """
    Показывает список ключей (на русском) в выбранной категории.
    """
    category_key = callback.data.split("_", 2)[-1]  # e.g., "text"
    keys_in_category = CONTENT_TYPES.get(category_key)

    if not keys_in_category:
        await callback.answer("Ошибка: категория не найдена.", show_alert=True)
        return

    buttons = []
    # Создаем кнопки для каждого ключа в категории
    for key in sorted(keys_in_category):
        display_name = KEY_NAMES.get(key, key)  # Получаем русское имя
        buttons.append([
            create_inline_button(
                text=display_name,
                callback_data=f"edit_{key}"
            )
        ])

    buttons.append([create_inline_button("« Назад (к категориям)", callback_data="back_to_categories")])
    keyboard = create_inline_keyboard(buttons)

    # Редактируем сообщение, чтобы не слать новое
    await callback.message.edit_text(
        f"Выбрана категория: <b>{CATEGORY_NAMES[category_key]}</b>\n\nВыберите, что хотите изменить:",
        reply_markup=keyboard
    )
    await state.set_state(ContentEdit.select_key)  # Устанавливаем состояние выбора ключа
    await callback.answer()


# Шаг 2.5: Кнопка "Назад" (возврат к Шагу 1)
@admin_content_router.callback_query(ContentEdit.select_key, F.data == "back_to_categories", IsAdmin(admin_ids))
async def go_back_to_categories(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя к выбору категорий (по сути, дублирует start_edit_content).
    """
    buttons = []
    for category_key, category_name in CATEGORY_NAMES.items():
        buttons.append([
            create_inline_button(
                text=category_name,
                callback_data=f"select_category_{category_key}"
            )
        ])

    buttons.append([create_inline_button("Отмена", callback_data="cancel_edit")])
    keyboard = create_inline_keyboard(buttons)

    await callback.message.edit_text(
        "Выберите категорию контента, которую хотите изменить:",
        reply_markup=keyboard
    )
    await state.set_state(ContentEdit.select_category)  # Возвращаем состояние выбора категории
    await callback.answer()


# Шаг 3: Обработка выбора Ключа
@admin_content_router.callback_query(ContentEdit.select_key, F.data.startswith("edit_"), IsAdmin(admin_ids))
async def select_key(callback: CallbackQuery, state: FSMContext):
    """Запрашивает новое значение для выбранного ключа и показывает текущее."""
    key = callback.data.replace("edit_", "")
    await state.update_data(selected_key=key)

    # Получаем русское имя для отображения
    display_name = KEY_NAMES.get(key, key)

    content_type = "text"
    for type_, keys in CONTENT_TYPES.items():
        if key in keys:
            content_type = type_
            break

    await state.update_data(content_type=content_type)  # Сохраняем тип для проверки

    current_value = await get_info_content(key)

    # Используем display_name в сообщениях
    if current_value:
        try:
            if content_type == "text":
                await callback.message.answer(f"Текущий текст для <b>{display_name}</b> (<code>{key}</code>):\n")
                await callback.message.answer(current_value)
                await callback.message.answer("Отправьте новый текст.\n")
            elif content_type == "photo":
                await callback.message.answer_photo(photo=current_value,
                                                    caption=f"Текущее фото для <b>{display_name}</b> (<code>{key}</code>).\n\nОтправьте новое фото.")
            elif content_type == "video":
                await callback.message.answer_video(video=current_value,
                                                    caption=f"Текущее видео для <b>{display_name}</b> (<code>{key}</code>).\n\nОтправьте новое видео.")
            elif content_type == "document":
                await callback.message.answer_document(document=current_value,
                                                       caption=f"Текущий документ для <b>{display_name}</b> (<code>{key}</code>).\n\nОтправьте новый документ.")
        except Exception as e:
            logger.error(f"Ошибка при показе текущего контента для {key}: {e}")
            await callback.message.answer(
                f"Не удалось показать текущий контент для <b>{display_name}</b> (<code>{key}</code>). Возможно, file_id устарел. Пожалуйста, отправьте новое значение.")
    else:
        await callback.message.answer(
            f"Для <b>{display_name}</b> (<code>{key}</code>) пока нет сохраненного контента. Пожалуйста, отправьте новое значение.")

    await callback.message.answer("Для отмены нажмите кнопку 'Отмена'.", reply_markup=cancel_keyboard)
    await state.set_state(ContentEdit.input_content)
    await callback.answer()


# Шаг 4: Обработка Ввода

@admin_content_router.message(ContentEdit.input_content, F.text, IsAdmin(admin_ids))
async def process_text(message: Message, state: FSMContext):
    """Обновляет текстовое значение с сохранением HTML-разметки."""
    if message.text and message.text.lower() == "отмена":
        await cancel_edit_process(message, state)
        return

    data = await state.get_data()
    key = data.get("selected_key")
    content_type = data.get("content_type")  # Получаем тип из FSM

    if content_type == "text":
        new_text = message.html_text
        await update_info_content(key, new_text)
        await message.answer(f"Текст для <code>{key}</code> обновлён.", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer(f"Ожидался {content_type}, а не текст. Пожалуйста, отправьте корректный формат.",
                             reply_markup=cancel_keyboard)
        # Не очищаем state, даем админу попробовать еще раз


@admin_content_router.message(ContentEdit.input_content, F.photo, IsAdmin(admin_ids))
async def process_photo(message: Message, state: FSMContext):
    """Обновляет токен фото в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    content_type = data.get("content_type")

    if content_type == "photo":
        photo_token = message.photo[-1].file_id
        await update_info_content(key, photo_token)
        await message.answer(f"Фото для <code>{key}</code> обновлено.", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer(f"Ожидался {content_type}, а не фото. Пожалуйста, отправьте корректный формат.",
                             reply_markup=cancel_keyboard)
        # Не очищаем state


@admin_content_router.message(ContentEdit.input_content, F.video, IsAdmin(admin_ids))
async def process_video(message: Message, state: FSMContext):
    """Обновляет токен видео в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    content_type = data.get("content_type")

    if content_type == "video":
        video_token = message.video.file_id
        await update_info_content(key, video_token)
        await message.answer(f"Видео для <code>{key}</code> обновлено.", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer(f"Ожидался {content_type}, а не видео. Пожалуйста, отправьте корректный формат.",
                             reply_markup=cancel_keyboard)
        # Не очищаем state


@admin_content_router.message(ContentEdit.input_content, F.document, IsAdmin(admin_ids))
async def process_document(message: Message, state: FSMContext):
    """Обновляет токен документа в базе."""
    data = await state.get_data()
    key = data.get("selected_key")
    content_type = data.get("content_type")

    if content_type == "document":
        document_token = message.document.file_id
        await update_info_content(key, document_token)
        await message.answer(f"Документ для <code>{key}</code> обновлён.", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer(f"Ожидался {content_type}, а не документ. Пожалуйста, отправьте корректный формат.",
                             reply_markup=cancel_keyboard)
        # Не очищаем state


# --- Хендлеры Отмены ---

@admin_content_router.callback_query(F.data == "cancel_edit", IsAdmin(admin_ids))
async def cancel_edit_inline(callback: CallbackQuery, state: FSMContext):
    """Отменяет процесс редактирования через инлайн-кнопку."""
    await callback.message.delete()
    await cancel_edit_process(callback.message, state)
    await callback.answer()


@admin_content_router.message(F.text.lower() == "отмена", IsAdmin(admin_ids))  # Используем lower() для надежности
async def cancel_edit_text_button(message: Message, state: FSMContext):
    """Отменяет процесс редактирования через текстовую кнопку."""
    await cancel_edit_process(message, state)


async def cancel_edit_process(message: Message, state: FSMContext):
    """Общая логика отмены редактирования контента."""
    current_state = await state.get_state()
    if current_state:  # Проверяем, есть ли активное состояние
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=main_keyboard)
    else:
        # Если нажали "Отмена" без активного состояния FSM (маловероятно, но возможно)
        await message.answer("Вы уже находитесь в главном меню.", reply_markup=main_keyboard)


# Обработка некорректного ввода
@admin_content_router.message(ContentEdit.input_content, IsAdmin(admin_ids))
async def invalid_input(message: Message, state: FSMContext):
    """Обрабатывает некорректный ввод (например, стикер или аудио)."""
    if message.text and message.text.lower() == "отмена":
        await cancel_edit_process(message, state)
        return

    data = await state.get_data()
    content_type = data.get("content_type", "ожидаемый формат")
    await message.answer(
        f"Ошибка. Ожидался {content_type}. Пожалуйста, отправьте корректный формат или нажмите 'Отмена'.",
        reply_markup=cancel_keyboard)
