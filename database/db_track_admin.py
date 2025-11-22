from logging import getLogger
from typing import Optional, List, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import update, select, delete

from .db_base import async_session
from .db_users import get_user_by_id
from .db_track_codes import TrackCode

logger = getLogger(__name__)


# --- УВЕДОМЛЕНИЯ ---

async def safe_send_notification(bot: Bot, track_code: str, chat_id: int, status: str, session) -> bool:
    """Безопасно отправляет уведомление и сбрасывает tg_id при блокировке."""
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
    """

    async with async_session() as session:
        for track_code, internal_id in codes_data:

            actual_tg_id = None
            if internal_id:
                user_info = await get_user_by_id(internal_id)
                if user_info: actual_tg_id = user_info.get('tg_id')

            track = (await session.execute(
                select(TrackCode).where(TrackCode.track_code == track_code)
            )).scalar_one_or_none()

            target_tg_id = None

            if track:
                track.status = status
                if actual_tg_id: track.tg_id = actual_tg_id

                target_tg_id = track.tg_id
            else:
                new_track = TrackCode(track_code=track_code, status=status, tg_id=actual_tg_id)
                session.add(new_track)
                target_tg_id = actual_tg_id

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
