from logging import getLogger
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, delete, BigInteger, String, update
from sqlalchemy.orm import Mapped, mapped_column

from .db_base import async_session, Base

logger = getLogger(__name__)

DEFAULT_TRACK_STATUS = "out_of_stock"


class TrackCode(Base):
    __tablename__ = 'track_codes'
    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String)
    tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def __repr__(self):
        return f"TrackCode(id={self.id}, code={self.track_code}, status={self.status}, tg_id={self.tg_id})"


# --- Функции для работы с трек-кодами ---

async def get_track_code_status(track_code: str) -> Optional[dict]:
    """
    Ищет трек-код в базе и возвращает его статус и TG ID владельца.
    Используется для проверки статуса пользователем.
    """
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status, TrackCode.tg_id)
            .where(TrackCode.track_code == track_code)
            .execution_options(autocommit=True)
        )
        row = result.one_or_none()

        if row:
            return {
                'track_code': row[0],
                'status': row[1],
                'tg_id': row[2]
            }
        return None


async def get_track_code_info(track_code: str) -> Optional[dict]:
    """
    Ищет трек-код в базе данных и возвращает полную информацию о нем:
    трек-код, статус и TG ID владельца. Используется в админ-панели для поиска.
    """
    logger.debug(f"В файле database/track_codes.py - Поиск трек-кода: '{track_code}'")
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status, TrackCode.tg_id)
            .where(TrackCode.track_code == track_code)
        )
        row = result.one_or_none()

        if row:
            logger.debug(
                f"В файле database/track_codes.py - Найден трек-код: {row[0]}, статус: {row[1]}, tg_id: {row[2]}")
            return {
                'track_code': row[0],
                'status': row[1],
                'tg_id': row[2]
            }
        else:
            logger.debug(f"В файле database/track_codes.py - Трек-код '{track_code}' не найден")
            return None


async def add_multiple_track_codes(track_codes: List[str], tg_id: int) -> Tuple[int, List[str]]:
    """
    Добавляет список трек-кодов в базу данных, если они еще не существуют,
    присваивая им статус по умолчанию и TG ID пользователя.
    Возвращает кортеж (количество добавленных, список добавленных кодов).
    """
    new_codes_added_count = 0
    added_codes: List[str] = []

    async with async_session() as session:
        for track_code in track_codes:
            # Проверяем, существует ли уже такой трек-код
            existing_track = await session.execute(
                select(TrackCode.id).where(TrackCode.track_code == track_code)
            )

            if existing_track.scalar_one_or_none() is None:
                # Если не существует, добавляем новый с DEFAULT_TRACK_STATUS
                new_track = TrackCode(
                    track_code=track_code,
                    status=DEFAULT_TRACK_STATUS,
                    tg_id=tg_id  # Привязываем к пользователю, который добавил
                )
                session.add(new_track)
                new_codes_added_count += 1
                added_codes.append(track_code)
        await session.commit()
        return new_codes_added_count, added_codes


async def delete_multiple_track_codes(track_codes: List[str]) -> int:
    """
    Удаляет трек-коды из базы данных по списку кодов.
    Возвращает количество удалённых записей.
    """
    async with async_session() as session:
        result = await session.execute(
            delete(TrackCode)
            .where(TrackCode.track_code.in_(track_codes))
        )
        deleted_count = result.rowcount
        await session.commit()
        return deleted_count


async def get_user_track_codes(tg_id: int) -> List[Tuple[str, str]]:
    """Возвращает список трек-кодов и их статусов для указанного пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.tg_id == tg_id)
        )
        return result.all()


async def check_or_add_track_code(track_code: str, tg_id: int) -> str:
    """Проверяет наличие трек-кода и добавляет его с привязкой к пользователю, если он отсутствует."""
    async with async_session() as session:
        async with session.begin():
            # Запрос с блокировкой для избежания состояния гонки
            stmt = select(TrackCode).where(TrackCode.track_code == track_code).with_for_update()
            query_result = await session.execute(stmt)
            tc = query_result.scalar_one_or_none()

            if tc:
                # Если код найден, но не привязан к пользователю, привязываем
                if tc.tg_id is None:
                    tc.tg_id = tg_id
                return tc.status
            else:
                # Если код не найден, создаем новый
                new_tc = TrackCode(
                    track_code=track_code,
                    status="out_of_stock",
                    tg_id=tg_id
                )
                session.add(new_tc)
                return "out_of_stock"


async def bulk_assign_track_codes(track_codes_list: List[str], user_id: int) -> Dict[str, Any]:
    """
    Массово привязывает список трек-кодов к указанному пользователю (tg_id).
    Если код существует, обновляет tg_id. Если код не существует, создает его.

    :param track_codes_list: Список трек-кодов для привязки.
    :param user_id: Telegram ID пользователя, которому присваиваются коды.
    :return: Словарь со статистикой: {"assigned_count": int, "created_count": int, "total_processed": int}
    """
    if not track_codes_list:
        return {"status": "error", "message": "Список трек-кодов пуст.", "total_processed": 0}

    # Удаляем дубликаты из входного списка
    unique_track_codes = list(set(track_codes_list))

    assigned_count = 0
    created_count = 0

    async with async_session() as session:
        # 1. Привязываем (обновляем) tg_id для всех существующих кодов в списке
        update_stmt = (
            update(TrackCode)
            .where(TrackCode.track_code.in_(unique_track_codes))
            .values(tg_id=user_id)
        )
        update_result = await session.execute(update_stmt)
        assigned_count = update_result.rowcount
        await session.commit()

        # 2. Находим коды, которые не были обновлены (т.е. их нет в БД)

        # Получаем список всех кодов из входного списка, которые теперь есть в БД
        existing_codes_result = await session.execute(
            select(TrackCode.track_code).where(TrackCode.track_code.in_(unique_track_codes))
        )
        # Преобразуем в множество для быстрого поиска
        existing_codes_set = {row[0] for row in existing_codes_result.all()}

        # Определяем коды, которые нужно создать
        codes_to_create = [code for code in unique_track_codes if code not in existing_codes_set]

        if codes_to_create:
            # Создаем новые записи, сразу привязывая их к пользователю
            new_tracks = [
                TrackCode(
                    track_code=code,
                    status=DEFAULT_TRACK_STATUS,
                    tg_id=user_id
                )
                for code in codes_to_create
            ]
            session.add_all(new_tracks)
            created_count = len(new_tracks)
            await session.commit()

        total_processed = len(unique_track_codes)
        logger.info(
            f"Массовая привязка кодов к пользователю {user_id}: Обновлено: {assigned_count}, Создано: {created_count}")

        return {
            "status": "success",
            "assigned_count": assigned_count,
            "created_count": created_count,
            "total_processed": total_processed
        }
