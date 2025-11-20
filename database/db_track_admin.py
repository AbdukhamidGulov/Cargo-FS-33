from logging import getLogger
from typing import Optional, List, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import update

from .db_base import async_session
from .db_users import get_user_by_id
from .db_track_codes import TrackCode, delete_multiple_track_codes

logger = getLogger(__name__)


# --- УВЕДОМЛЕНИЯ ---

async def safe_send_notification(bot: Bot, track_code: str, chat_id: int, status: str, session) -> bool:
    """Безопасно отправляет уведомление и сбрасывает tg_id при блокировке."""
    # ... (код функции safe_send_notification, который ты предоставлял ранее) ...
    texts = {
        "in_stock": f"Ваш товар <code>{track_code}</code> <b>прибыл на склад</b>.",
        "shipped": f"Ваш товар <code>{track_code}</code> <b>отправлен</b>.",
        "arrived": f"Ваш товар <code>{track_code}</code> <b>прибыл в пункт выдачи</b>! (@fir2201)"
    }

    text = texts.get(status)
    if not text: return False

    try:
        await bot.send_message(chat_id, text)
        return True
    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower() or "blocked" in str(e).lower():
            logger.warning(f"Чат {chat_id} недоступен. Сбрасываем привязку для {track_code}.")
            # Используем session, переданный из add_or_update_track_codes_list
            await session.execute(
                update(TrackCode).where(TrackCode.track_code == track_code).values(tg_id=None)
            )
        return False
    except Exception as e:
        logger.error(f"Ошибка отправки {track_code} -> {chat_id}: {e}")
        return False


async def add_or_update_track_codes_list(codes_data: List[Tuple[str, Optional[int]]], status: str, bot: Bot) -> None:
    """
    Массовое обновление статусов/привязок с уведомлениями.
    Использует функции из db_users и db_track_codes.
    """
    from .db_track_codes import update_track_code, create_track_code, get_track_code  # Избегаем циклического импорта

    async with async_session() as session:
        for track_code, internal_id in codes_data:

            # 1. Получаем реальный TG ID по внутреннему ID пользователя
            actual_tg_id = None
            if internal_id:
                user_info = await get_user_by_id(internal_id)
                if user_info: actual_tg_id = user_info.get('tg_id')

            # 2. Ищем трек в базе (используем session, чтобы потом использовать его для update(tg_id=None))
            track = (await session.execute(
                select(TrackCode).where(TrackCode.track_code == track_code)
            )).scalar_one_or_none()

            target_tg_id = None

            if track:
                # Обновляем статус
                track.status = status
                # Если передали нового владельца - обновляем
                if actual_tg_id: track.tg_id = actual_tg_id

                target_tg_id = track.tg_id
            else:
                # Создаем новый
                new_track = TrackCode(track_code=track_code, status=status, tg_id=actual_tg_id)
                session.add(new_track)
                target_tg_id = actual_tg_id

            # 3. Уведомление
            if target_tg_id:
                await safe_send_notification(bot, track_code, target_tg_id, status, session)

        await session.commit()


# --- АДМИН-УДАЛЕНИЕ ---

async def delete_shipped_track_codes() -> int:
    """Удаляет все трек-коды со статусом 'shipped'."""
    async with async_session() as session:
        result = await session.execute(
            delete(TrackCode).where(TrackCode.status == "shipped")
        )
        await session.commit()
        return result.rowcount