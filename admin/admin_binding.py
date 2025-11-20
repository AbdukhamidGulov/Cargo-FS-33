from logging import getLogger

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from database.db_track_codes import check_track_codes_existence, bulk_assign_track_codes
from database.db_users import get_user_by_id
from keyboards import cancel_keyboard, main_keyboard
from filters_and_config import IsAdmin, admin_ids
from utils.message_common import extract_text_from_message

admin_bulk_router = Router()
logger = getLogger(__name__)


class BindTrackStates(StatesGroup):
    waiting_for_track_codes = State()
    waiting_for_user_id = State()


# --- ОБЩАЯ ОТМЕНА ---
@admin_bulk_router.message(BindTrackStates.waiting_for_track_codes, F.text.lower() == "отмена")
@admin_bulk_router.message(BindTrackStates.waiting_for_user_id, F.text.lower() == "отмена")
async def cancel_process(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Массовая привязка отменена.", reply_markup=main_keyboard)


# --- 1. ЗАПРОС СПИСКА КОДОВ ---
@admin_bulk_router.message(F.text == "Массовая привязка трек-кодов", IsAdmin(admin_ids))
async def start_bulk_bind(message: Message, state: FSMContext):
    await state.set_state(BindTrackStates.waiting_for_track_codes)
    await message.answer(
        "📦 <b>Массовая привязка</b>\n\n"
        "Отправьте список трек-кодов (текстом или .txt файлом).",
        reply_markup=cancel_keyboard
    )


# --- 2. ОБРАБОТКА КОДОВ И ПРОВЕРКА В БД ---
@admin_bulk_router.message(BindTrackStates.waiting_for_track_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    # Используем extract_text_from_message с bot
    raw_content = await extract_text_from_message(message, bot)

    if not raw_content:
        await message.answer("❌ Не удалось извлечь данные.", reply_markup=cancel_keyboard)
        return

    # Превращаем текст в список уникальных кодов
    track_codes = list(set([line.strip() for line in raw_content.splitlines() if line.strip()]))

    if not track_codes:
        await message.answer("❌ Список трек-кодов пуст.", reply_markup=cancel_keyboard)
        return

    await message.answer(f"⏳ Проверка <b>{len(track_codes)}</b> кодов в базе данных...")

    existing_list, non_existing_codes = await check_track_codes_existence(track_codes)

    if not existing_list and not non_existing_codes:
        await message.answer("❌ В списке нет кодов для обработки.", reply_markup=cancel_keyboard)
        return

    await state.update_data(
        codes_to_bind=[item['code'] for item in existing_list],  # Коды, которые существуют и будут привязаны
        non_existing=non_existing_codes,  # Коды, которые будут созданы (если bulk_assign их не найдет)
        initial_list_size=len(track_codes)  # Размер оригинального списка
    )

    # Подготовка отчета для админа
    text = (
        f"✅ <b>Проверка завершена</b> (из {len(track_codes)} уникальных кодов)\n"
        f"Найдено в базе: <b>{len(existing_list)}</b>\n"
        f"Не найдено в базе: <b>{len(non_existing_codes)}</b>"
    )

    if non_existing_codes:
        preview = "\n".join(non_existing_codes[:5])
        text += f"\n\n<i>Первые 5 не найденных:</i>\n<code>{preview}</code>"

    text += "\n\nВведите внутренний ID пользователя (например: <b>FS1234</b> или просто <b>1234</b>):"

    await state.set_state(BindTrackStates.waiting_for_user_id)
    await message.answer(text, reply_markup=cancel_keyboard)


# --- 3. ОБРАБОТКА ID ПОЛЬЗОВАТЕЛЯ И ПРИВЯЗКА ---
@admin_bulk_router.message(BindTrackStates.waiting_for_user_id)
async def process_user_binding(message: Message, state: FSMContext):
    user_input = message.text.strip().upper().replace("FS", "")

    if not user_input.isdigit():
        await message.answer("❌ Неверный формат ID. Введите число или FSxxxx.")
        return

    user_id = int(user_input)
    # Используем FS-ID для получения TG ID
    user_data = await get_user_by_id(user_id)

    if not user_data:
        await message.answer(f"❌ Пользователь FS{user_id:04d} не найден в базе пользователей.")
        return

    data = await state.get_data()
    codes_to_bind = data.get('codes_to_bind', [])
    non_existing_codes = data.get('non_existing', [])

    # Список кодов, которые будут отправлены на массовое обновление/создание
    all_codes_to_process = codes_to_bind + non_existing_codes

    tg_id = user_data.get('tg_id')
    if not tg_id:
        await message.answer("❌ У пользователя отсутствует Telegram ID (tg_id) для привязки.")
        return

    if not all_codes_to_process:
        await message.answer("❌ Нет кодов для привязки. Отменено.", reply_markup=main_keyboard)
        await state.clear()
        return

    await message.answer(f"🔗 Привязываю {len(all_codes_to_process)} кодов к FS{user_id:04d}...")

    # Массовая привязка/создание в один запрос
    stats = await bulk_assign_track_codes(all_codes_to_process, tg_id)

    success_count = stats['assigned'] + stats['created']

    # Итоговый отчет
    res_text = (
        f"📊 <b>Итог массовой привязки</b> (Всего в списке: {data.get('initial_list_size', 0)})\n"
        f"👤 Пользователь: <code>FS{user_id:04d}</code> ({user_data.get('name', '???')})\n"
        f"✅ Всего обработано: <b>{success_count}</b>\n"
        f"   ├ Обновлено (перепривязано): {stats['assigned']}\n"
        f"   └ Создано (новые коды): {stats['created']}"
    )

    await message.answer(res_text, reply_markup=main_keyboard)
    await state.clear()
