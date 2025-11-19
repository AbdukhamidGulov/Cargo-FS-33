from logging import getLogger

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from database.db_track_codes import get_track_code, bulk_assign_track_codes
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


# --- ЛОГИКА ---
@admin_bulk_router.message(F.text == "Массовая привязка трек-кодов", IsAdmin(admin_ids))
async def start_bulk_bind(message: Message, state: FSMContext):
    await state.set_state(BindTrackStates.waiting_for_track_codes)
    await message.answer(
        "📦 <b>Массовая привязка</b>\n\n"
        "Отправьте список трек-кодов (текстом или .txt файлом).\n"
        "Каждый код с новой строки.",
        reply_markup=cancel_keyboard
    )


@admin_bulk_router.message(BindTrackStates.waiting_for_track_codes)
async def process_track_codes(message: Message, state: FSMContext, bot: Bot):
    raw_text = await extract_text_from_message(message, bot)

    if not raw_text:
        await message.answer(
            "❌ Не удалось извлечь данные. Отправьте текст или .txt файл в UTF-8.",
            reply_markup=cancel_keyboard
        )
        return

    # Превращаем текст в список, убирая пустые строки
    track_codes = [line.strip() for line in raw_text.splitlines() if line.strip()]

    if not track_codes:
        await message.answer("❌ Список трек-кодов пуст.", reply_markup=cancel_keyboard)
        return

    await message.answer(f"⏳ Проверка {len(track_codes)} кодов в БД...")

    valid_codes = []
    invalid_codes = []

    # ⚠️ ВНИМАНИЕ: Цикл for остался, так как функция bulk_assign_track_codes только
    # привязывает/создает, но не возвращает статусы кодов. Для отображения
    # найденных/ненайденных кодов перед привязкой, пока используем поэлементную проверку.
    for code in track_codes:
        info = await get_track_code(code)
        if info:
            valid_codes.append((code, info['status']))
        else:
            invalid_codes.append(code)

    if not valid_codes:
        await message.answer("❌ Ни один код не найден в базе.", reply_markup=cancel_keyboard)
        return

    await state.update_data(valid=valid_codes, invalid=invalid_codes)

    text = (
        f"✅ <b>Проверка завершена</b>\n"
        f"Найдено: <b>{len(valid_codes)}</b>\n"
        f"Не найдено: <b>{len(invalid_codes)}</b>"
    )

    if invalid_codes:
        preview = "\n".join(invalid_codes[:10])
        text += f"\n\n<i>Не найдены (первые 10):</i>\n<code>{preview}</code>"

    text += "\n\nВведите ID пользователя (например: <b>FS1234</b> или просто <b>1234</b>):"

    await state.set_state(BindTrackStates.waiting_for_user_id)
    await message.answer(text, reply_markup=cancel_keyboard)


@admin_bulk_router.message(BindTrackStates.waiting_for_user_id)
async def process_user_binding(message: Message, state: FSMContext):
    user_input = message.text.strip().upper().replace("FS", "")

    if not user_input.isdigit():
        await message.answer("❌ Неверный формат ID. Введите число или FSxxxx.")
        return

    user_id = int(user_input)
    user_data = await get_user_by_id(user_id)

    if not user_data:
        await message.answer(f"❌ Пользователь FS{user_id:04d} не найден.")
        return

    data = await state.get_data()
    valid_codes = data.get('valid', [])

    tg_id = user_data.get('tg_id')
    if not tg_id:
        await message.answer("❌ У пользователя отсутствует Telegram ID для привязки.")
        return

    await message.answer(f"🔗 Привязываю {len(valid_codes)} кодов к FS{user_id:04d}...")

    # 1. Извлекаем только коды из списка кортежей (code, status)
    codes_to_bind = [code for code, _ in valid_codes]

    stats = await bulk_assign_track_codes(codes_to_bind, tg_id)

    success_count = stats['assigned'] + stats['created']
    invalid_codes_count = len(data.get('invalid', []))

    # Итоговый отчет
    res_text = (
        f"📊 <b>Итог массовой привязки</b>\n"
        f"👤 Пользователь: <code>FS{user_id:04d}</code> ({user_data.get('name', '???')})\n"
        f"✅ Всего успешно обработано: <b>{success_count}</b>\n"
        f"   ├ Обновлено (перепривязано): {stats['assigned']}\n"
        f"   └ Создано (новые коды): {stats['created']}"
    )

    if invalid_codes_count > 0:
        res_text += f"\n\n⚠️ Кодов не найдено в базе: {invalid_codes_count}"

    await message.answer(res_text, reply_markup=main_keyboard)
    await state.clear()
