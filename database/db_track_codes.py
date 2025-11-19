from logging import getLogger
from typing import Optional, List, Tuple, Dict

from sqlalchemy import select, delete, update, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .db_base import async_session, Base

logger = getLogger(__name__)

DEFAULT_TRACK_STATUS = "out_of_stock"


class TrackCode(Base):
    __tablename__ = 'track_codes'

    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(String, unique=True, index=True)  # Добавил index для скорости
    status: Mapped[str] = mapped_column(String, default=DEFAULT_TRACK_STATUS)
    tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def __repr__(self):
        return f"<TrackCode(code={self.track_code}, status={self.status}, tg_id={self.tg_id})>"


# --- ОПТИМИЗИРОВАННЫЕ ФУНКЦИИ ---

async def get_track_code(track_code: str) -> Optional[dict]:
    """Функция получения информации о трек-коде."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status, TrackCode.tg_id)
            .where(TrackCode.track_code == track_code)
        )
        row = result.one_or_none()

        if row:
            return {'track_code': row[0], 'status': row[1], 'tg_id': row[2]}
        return None


async def add_multiple_track_codes(track_codes: List[str], tg_id: int) -> Tuple[int, List[str]]:
    """
    Массовое добавление трек-кодов.
    """
    if not track_codes:
        return 0, []

    unique_codes = list(set(track_codes))

    async with async_session() as session:
        # 1. Находим, какие коды УЖЕ есть в базе
        existing_stmt = select(TrackCode.track_code).where(TrackCode.track_code.in_(unique_codes))
        existing_result = await session.execute(existing_stmt)
        existing_set = {row[0] for row in existing_result.all()}

        # 2. Отфильтровываем новые
        new_codes_to_insert = [
            TrackCode(track_code=code, status=DEFAULT_TRACK_STATUS, tg_id=tg_id)
            for code in unique_codes if code not in existing_set
        ]

        if new_codes_to_insert:
            session.add_all(new_codes_to_insert)
            await session.commit()

            added_list = [t.track_code for t in new_codes_to_insert]
            logger.info(f"Добавлено {len(added_list)} новых треков пользователем {tg_id}")
            return len(added_list), added_list

        return 0, []


async def delete_multiple_track_codes(track_codes: List[str]) -> int:
    """Массовое удаление по списку."""
    if not track_codes:
        return 0

    async with async_session() as session:
        result = await session.execute(
            delete(TrackCode).where(TrackCode.track_code.in_(track_codes))
        )
        await session.commit()
        return result.rowcount


async def get_user_track_codes(tg_id: int) -> List[Tuple[str, str]]:
    """Получение всех треков пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.tg_id == tg_id)
        )
        return result.all()


async def bulk_assign_track_codes(track_codes_list: List[str], user_tg_id: int) -> Dict[str, int]:
    """
    Умная массовая привязка.
    1. Обновляет существующие.
    2. Создает несуществующие.
    """
    if not track_codes_list:
        return {"assigned": 0, "created": 0}

    unique_codes = list(set(track_codes_list))

    async with async_session() as session:
        # 1. Массовое обновление существующих (UPDATE)
        update_stmt = (
            update(TrackCode)
            .where(TrackCode.track_code.in_(unique_codes))
            .values(tg_id=user_tg_id)
        )
        update_result = await session.execute(update_stmt)
        assigned_count = update_result.rowcount

        # 2. Поиск тех, которых нет (для создания)
        # Получаем список тех, что есть в базе (включая только что обновленные)
        existing_res = await session.execute(
            select(TrackCode.track_code).where(TrackCode.track_code.in_(unique_codes))
        )
        existing_in_db = {row[0] for row in existing_res.all()}

        # Вычисляем разницу: (Все из списка) - (Те, что есть в БД) = (Новые)
        codes_to_create = [
            TrackCode(track_code=code, status=DEFAULT_TRACK_STATUS, tg_id=user_tg_id)
            for code in unique_codes if code not in existing_in_db
        ]

        created_count = 0
        if codes_to_create:
            session.add_all(codes_to_create)
            created_count = len(codes_to_create)

        await session.commit()

        return {
            "assigned": assigned_count,
            "created": created_count,
            "total": len(unique_codes)
        }
