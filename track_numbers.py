import re
from logging import getLogger

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, base

from database.track_codes import add_multiple_track_codes
from keyboards import main_keyboard, cancel_keyboard, add_track_codes_follow_up_keyboard

track_code_router = Router()
logger = getLogger(__name__)

# Шаблон для поиска трек-кодов:
# Ищем последовательности из 8 и более символов, состоящие из латинских букв (A-Z) и цифр (0-9).
TRACK_CODE_PATTERN = r'[A-Z0-9]{8,}'

status_messages = {
    "in_stock": "Ваш товар уже на складе.",
    "out_of_stock": "Не на складе.",
    "shipped": "Ваш товар был отправлен.",
    "arrived": "Ваш товар прибыл в пункт выдачи! Свяжитесь с администратором: @fir2201"
}


class TrackCodeStates(StatesGroup):
    """Состояния для обработки ввода трек-кодов. Состояния используются в обоих файлах."""
    check_single_code = State()
    add_multiple_codes = State()  # Для массового добавления трек-кодов


# --- Вспомогательная функция для запуска режима добавления трек-кодов ---
async def start_add_codes_process(responder: base.TelegramObject, state: FSMContext, user_id: int) -> None:
    """Общая логика запуска процесса добавления трек-кодов, вызываемая как из Message, так и из CallbackQuery."""
    await responder.answer(
        "Отправьте <b>трек-код или список трек-кодов</b> для отслеживания.\n"
        "Вы можете вставить текст любого формата: бот автоматически извлечет все коды, разделенные пробелом, запятой или новой строкой.\n\n"
        "Пример:\n"
        "<code>78948163753575, YT7577043820770 описание</code>\n\n"
        "Коды будут добавлены в ваш список отслеживания.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(TrackCodeStates.add_multiple_codes)
    logger.info(f"Пользователь {user_id} начал добавление трек-кодов.")


# ************************************************
# 1. МАССОВОЕ ДОБАВЛЕНИЕ ТРЕК-КОДОВ
# ************************************************

@track_code_router.message(F.text == "Добавить трек-кода")
async def add_track_codes(message: Message, state: FSMContext) -> None:
    """Запускает процесс добавления одного или нескольких трек-кодов (через кнопку ReplyKeyboardMarkup)."""
    await start_add_codes_process(message, state, message.from_user.id)


@track_code_router.message(TrackCodeStates.add_multiple_codes)
async def process_multiple_track_codes(message: Message, state: FSMContext) -> None:
    """Обрабатывает список трек-кодов, добавленных пользователем (один или несколько)."""
    if message.text == "Отмена":
        await message.answer("Режим добавления трек-кодов завершён.", reply_markup=main_keyboard)
        await state.clear()
        logger.info(f"Пользователь {message.from_user.id} завершил добавление трек-кодов.")
        return

    tg_id: int = message.from_user.id
    raw_text = message.text

    # ИСПОЛЬЗУЕМ ПОЗИТИВНУЮ ФИЛЬТРАЦИЮ: Извлекаем только те строки, которые соответствуют шаблону.
    input_codes = re.findall(TRACK_CODE_PATTERN, raw_text, re.IGNORECASE)

    # Удаляем дубликаты
    input_codes = list(set(input_codes))

    if not input_codes:
        await message.answer(
            "В тексте не удалось найти ни одного трек-кода, пригодного для добавления. "
            "Пожалуйста, убедитесь, что вы правильно их скопировали.",
            reply_markup=cancel_keyboard
        )
        return

    try:
        # ВНИМАНИЕ: Предполагается, что add_multiple_track_codes возвращает
        # кортеж (количество_добавлено, список_добавленных_кодов)
        result = await add_multiple_track_codes(input_codes, tg_id)

        # Проверяем, что возвращаемое значение является кортежем с двумя элементами
        if isinstance(result, tuple) and len(result) == 2:
            added_count, added_codes = result
        else:
            # Если возвращается только количество, используем его и пустой список для кодов
            added_count = result
            added_codes = []
            logger.warning("add_multiple_track_codes не вернула список добавленных кодов.")

        # ФУНКЦИЯ ДАЕТ ИНФОРМАЦИЮ О РЕЗУЛЬТАТЕ ДОБАВЛЕНИЯ
        response_parts = [f"Обработано <b>{len(input_codes)}</b> потенциальных трек-кодов."]

        if added_count > 0:
            # 1. Показываем список добавленных кодов
            added_codes_list_text = "\n".join([f"• <code>{code}</code>" for code in added_codes])

            # 2. Убрано упоминание статуса в скобках
            response_parts.append(
                f"✅ Успешно добавлены <b>{added_count}</b> трек-коды в ваш список отслеживания:\n"
                f"{added_codes_list_text}"
            )

        # Информируем о пропущенных (уже существующих)
        skipped_count = len(input_codes) - added_count
        if skipped_count > 0:
            response_parts.append(
                f"\n⏭️ <b>{skipped_count}</b> трек-кодов уже отслеживаются вами или другими пользователями и были пропущены."
            )

        # --- РАЗДЕЛЕНИЕ СООБЩЕНИЙ И ИЗМЕНЕНИЕ КЛАВИАТУРЫ ---

        # 1. Основное сообщение о результате
        await message.answer("\n".join(response_parts), reply_markup=main_keyboard)
        logger.info(f"Пользователь {tg_id} добавил {added_count} новых трек-кодов (всего {len(input_codes)}).")
        await state.clear()  # Очищаем FSMState

        # 2. Сообщение с дополнительными действиями (inline-клавиатура)
        await message.answer(
            "Что вы хотите сделать дальше?",
            reply_markup=add_track_codes_follow_up_keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка при массовом добавлении трек-кодов для пользователя {tg_id}: {e}")
        await message.answer(
            "Произошла ошибка при добавлении трек-кодов. Попробуйте позже или обратитесь к администратору.",
            reply_markup=cancel_keyboard
        )


# ************************************************
# 2. ДОПОЛНИТЕЛЬНЫЕ ДЕЙСТВИЯ ПОСЛЕ ДОБАВЛЕНИЯ (Inline Handlers)
# ************************************************

@track_code_router.callback_query(F.data == "add_more_track_codes")
async def restart_add_track_codes(callback: CallbackQuery, state: FSMContext) -> None:
    """Перезапускает процесс массового добавления трек-кодов по нажатию inline-кнопки."""
    await callback.message.delete() # Удаляем предыдущее сообщение с кнопками
    # Используем общую вспомогательную функцию для запуска режима добавления
    await start_add_codes_process(callback.message, state, callback.from_user.id)
    await callback.answer() # Отключаем "часики" на кнопке
