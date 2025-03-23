from logging import getLogger
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import String, select, update, delete, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from .base import async_session, Base, engine

logger = getLogger(__name__)

class TrackCode(Base):
    __tablename__ = 'track_codes'
    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(String(50))
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

    def to_dict(self) -> dict:
        """Преобразует объект трек-кода в словарь."""
        return {
            "id": self.id,
            "track_code": self.track_code,
            "status": self.status,
            "tg_id": self.tg_id,
        }


async def drop_track_codes_table():
    """Удаляет таблицу track_codes из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.tables['track_codes'].drop(sync_conn))


async def get_track_codes_list() -> list[dict]:
    """Возвращает список всех трек-кодов с их статусами и Telegram ID."""
    async with async_session() as session:
        result = await session.execute(select(TrackCode))
        return [tc.to_dict() for tc in result.scalars()]


async def get_user_track_codes(tg_id: int) -> list[tuple]:
    """Возвращает список трек-кодов и их статусов для указанного пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status).where(TrackCode.tg_id == tg_id)
        )
        return [(row.track_code, row.status) for row in result]


async def update_or_add_track_code(session, track_code: str, status: str) -> TrackCode:
    """Обновляет статус существующего трек-кода или добавляет новый."""
    stmt = select(TrackCode).filter_by(track_code=track_code)
    result = await session.execute(stmt)
    track_code_obj = result.scalar_one_or_none()
    if track_code_obj:
        track_code_obj.status = status
    else:
        track_code_obj = TrackCode(track_code=track_code, status=status, tg_id=None)
        session.add(track_code_obj)
    return track_code_obj

async def notify_user(bot, track_code_obj: TrackCode, message) -> None:
    """Отправляет уведомление пользователю о статусе его трек-кода."""
    if track_code_obj.tg_id:
        status_text = "на складе" if track_code_obj.status == "in_stock" else "отправлен"
        try:
            await bot.send_message(
                track_code_obj.tg_id,
                f"Ваш товар с трек-кодом <code>{track_code_obj.track_code}</code> {status_text}."
            )
        except TelegramBadRequest as e:
            if "chat not found" in str(e):
                async with async_session() as session:
                    async with session.begin():
                        await session.execute(
                            update(TrackCode).where(TrackCode.id == track_code_obj.id).values(tg_id=None)
                        )
                await bot.send_message(
                    message.from_user.id,
                    f"Не удалось отправить сообщение пользователю {track_code_obj.tg_id}: {e}"
                )
            else:
                await bot.send_message(message.from_user.id, f"Ошибка при отправке сообщения: {e}")

async def add_or_update_track_codes_list(track_codes: list[str], status: str, bot, message) -> None:
    """Добавляет или обновляет список трек-кодов с указанным статусом и отправляет уведомления."""
    async with async_session() as session:
        for track in track_codes:
            async with session.begin():
                track_code_obj = await update_or_add_track_code(session, track, status)
                await notify_user(bot, track_code_obj, message)


async def check_or_add_track_code(track_code: str, tg_id: int) -> str:
    """Проверяет наличие трек-кода в базе данных.
    Если трек-код есть, обновляет tg_id (если он был None) и возвращает текущий статус.
    Если трек-кода нет, добавляет его со статусом "out_of_stock" и возвращает "out_of_stock"."""
    async with async_session() as session:
        async with session.begin():
            stmt = select(TrackCode).filter_by(track_code=track_code)
            result = await session.execute(stmt)
            track_code_obj = result.scalar_one_or_none()

            if track_code_obj:
                if track_code_obj.tg_id is None:  # Обновляем tg_id, если он был None
                    track_code_obj.tg_id = tg_id
                    await session.commit()
                return track_code_obj.status
            else:  # Добавляем новый трек-код со статусом "out_of_stock"
                new_track_code = TrackCode(track_code=track_code, status="out_of_stock", tg_id=tg_id)
                session.add(new_track_code)
                await session.commit()
                return "out_of_stock"


async def delete_shipped_track_codes() -> None:
    """Удаляет все трек-коды со статусом 'shipped' из таблицы track_codes."""
    async with async_session() as session:
        await session.execute(delete(TrackCode).where(TrackCode.status == 'shipped'))
        await session.commit()
