from logging import getLogger
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete, BigInteger, update, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import async_session, Base, engine

logger = getLogger(__name__)

class TrackCode(Base):
    __tablename__ = 'track_codes'
    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String)
    tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def __repr__(self):
        return f"TrackCode(id={self.id}, code={self.track_code}, status={self.status}, tg_id={self.tg_id})"


async def drop_track_codes_table():
    """Удаляет таблицу track_codes из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[TrackCode.__table__])


async def get_track_codes_list() -> list[dict]:
    """Возвращает список всех трек-кодов с их статусами и Telegram ID."""
    async with async_session() as session:
        result = await session.execute(select(TrackCode))
        return [{
            "id": tc.id,
            "track_code": tc.track_code,
            "status": tc.status,
            "tg_id": tc.tg_id
        } for tc in result.scalars()]


async def get_user_track_codes(tg_id: int) -> list[tuple[str, str]]:
    """Возвращает список трек-кодов и их статусов для указанного пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.tg_id == tg_id)
        )
        return result.all()


async def add_or_update_track_codes_list(track_codes: list[str], status: str, bot) -> None:
    """Добавляет или обновляет список трек-кодов в базе данных и отправляет уведомления."""
    async with async_session() as session:
        for track_code in track_codes:
            # Проверяем, существует ли трек-код
            existing = await session.execute(select(TrackCode).where(TrackCode.track_code == track_code))
            existing = existing.scalar_one_or_none()
            if existing:
                existing.status = status  # Если существует, обновляем статус
                if existing.tg_id:  # Если есть tg_id, отправляем уведомление
                    await safe_send_notification(bot, track_code, existing.tg_id, status, session)
            else:
                # Если не существует, добавляем новую запись
                new_track_code = TrackCode(track_code=track_code, status=status, tg_id=None)
                session.add(new_track_code)  # Добавляем в сессию
        await session.commit()  # Сохраняем все изменения


async def safe_send_notification(bot: Bot, track_code: str, chat_id: int, status: str, session) -> bool:
    """Безопасно отправляет уведомление пользователю и обновляет tg_id при ошибке."""
    if not chat_id:  # Если chat_id отсутствует
        return False

    try:
        status_text = "на складе" if status == "in_stock" else "отправлен"
        logger.debug(status_text)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Ваш товар с трек-кодом <code>{track_code}</code> {status_text}."
        )
        logger.debug(f"Уведомление отправлено пользователю {chat_id} для трек-кода {track_code}")
        return True
    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower() or "blocked" in str(e).lower():
            logger.warning(f"Не удалось отправить уведомление: чат {chat_id} не найден или бот заблокирован")
            await session.execute(
                update(TrackCode).where(TrackCode.track_code == track_code).values(tg_id=None)
            ) # Обновляем tg_id на None в базе
            await session.commit()
        else:
            logger.error(f"Ошибка Telegram API для {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке уведомления {chat_id}: {e}")
        return False



async def check_or_add_track_code(track_code: str, tg_id: int) -> str:
    """Оптимизированная проверка/добавление трек-кода."""
    async with async_session() as session:
        async with session.begin():
            # Блокировка строки для предотвращения race condition
            stmt = select(TrackCode).where(TrackCode.track_code == track_code).with_for_update()
            result = await session.execute(stmt)
            tc = result.scalar_one_or_none()

            if tc:
                if tc.tg_id is None:
                    tc.tg_id = tg_id
                return tc.status
            else:
                new_tc = TrackCode(
                    track_code=track_code,
                    status="out_of_stock",
                    tg_id=tg_id
                )
                session.add(new_tc)
                return "out_of_stock"


async def delete_shipped_track_codes() -> int:
    """Удаляет отправленные трек-коды, возвращает количество удалённых."""
    async with async_session() as session:
        result = await session.execute(
            delete(TrackCode)
            .where(TrackCode.status == 'shipped')
            .returning(TrackCode.id)
        )
        deleted_count = len(result.all())
        await session.commit()
        return deleted_count
