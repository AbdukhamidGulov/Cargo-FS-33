from logging import getLogger
from typing import Optional, List, Tuple, Dict

from sqlalchemy import select, delete, update, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .db_base import async_session, Base, engine

logger = getLogger(__name__)

DEFAULT_TRACK_STATUS = "out_of_stock"


class TrackCode(Base):
    __tablename__ = 'track_codes'

    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default=DEFAULT_TRACK_STATUS)
    tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def __repr__(self):
        return f"<TrackCode(code={self.track_code}, status={self.status}, tg_id={self.tg_id})>"


# --- ЧТЕНИЕ (READ) ---

async def get_track_code(track_code: str) -> Optional[dict]:
    """Получает трек-код по его номеру (объединяет get_track_code_status/info)."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status, TrackCode.tg_id)
            .where(TrackCode.track_code == track_code)
        )
        row = result.one_or_none()
        if row: return {'track_code': row[0], 'status': row[1], 'tg_id': row[2]}
        return None


async def get_user_track_codes(tg_id: int) -> List[Tuple[str, str]]:
    """Получает все треки пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.tg_id == tg_id)
        )
        return result.all()


async def get_all_track_codes() -> List[Dict]:
    """Получает все трек-коды для отчета."""
    async with async_session() as session:
        result = await session.execute(select(TrackCode))
        return [{
            "id": tc.id,
            "track_code": tc.track_code,
            "status": tc.status,
            "tg_id": tc.tg_id
        } for tc in result.scalars()]


async def check_track_codes_existence(track_codes: List[str]) -> Tuple[List[Dict], List[str]]:
    """
    Проверяет существование списка кодов и возвращает их статус (для массовой привязки).
    Возвращает: (существующие_коды_с_инфо, несуществующие_коды)
    """
    if not track_codes:
        return [], []

    unique_codes = list(set(track_codes))

    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.track_code.in_(unique_codes))
        )
        existing_info = result.all()

        existing_codes_set = {row[0] for row in existing_info}
        non_existing_codes = [code for code in unique_codes if code not in existing_codes_set]

        existing_list = [{'code': row[0], 'status': row[1]} for row in existing_info]

        return existing_list, non_existing_codes


# --- ОПЕРАЦИИ (CREATE / UPDATE) ---

async def create_track_code(track_code: str, status: str, tg_id: Optional[int] = None) -> None:
    """Создает новый трек-код."""
    async with async_session() as session:
        new_track = TrackCode(track_code=track_code, status=status, tg_id=tg_id)
        session.add(new_track)
        await session.commit()


async def update_track_code(track_code: str, status: Optional[str] = None, tg_id: Optional[int] = None) -> bool:
    """Обновляет статус или TG ID существующего трек-кода."""
    update_data = {}
    if status is not None: update_data['status'] = status
    if tg_id is not None: update_data['tg_id'] = tg_id

    if not update_data: return False

    async with async_session() as session:
        result = await session.execute(
            update(TrackCode).where(TrackCode.track_code == track_code).values(**update_data)
        )
        await session.commit()
        return result.rowcount > 0


async def check_or_add_track_code(track_code: str, tg_id: int) -> str:
    """
    ВОССТАНОВЛЕНА. Проверяет наличие трек-кода и добавляет его с привязкой к пользователю,
    если он отсутствует (используется клиентом для одиночного ввода).
    """
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
                # Возвращаем текущий статус
                return tc.status
            else:
                # Если код не найден, создаем новый
                new_tc = TrackCode(
                    track_code=track_code,
                    status=DEFAULT_TRACK_STATUS,
                    tg_id=tg_id
                )
                session.add(new_tc)
                # Возвращаем статус по умолчанию
                return DEFAULT_TRACK_STATUS


# --- МАССОВЫЕ ОПЕРАЦИИ (BULK) ---

async def bulk_assign_track_codes(track_codes_list: List[str], user_tg_id: int) -> Dict[str, int]:
    """
    Массово привязывает (UPDATE) существующие и создает (INSERT) отсутствующие.
    Возвращает: {"assigned": int, "created": int}
    """
    if not track_codes_list: return {"assigned": 0, "created": 0}

    unique_codes = list(set(track_codes_list))

    async with async_session() as session:
        # 1. Update существующих
        res = await session.execute(
            update(TrackCode)
            .where(TrackCode.track_code.in_(unique_codes))
            .values(tg_id=user_tg_id)
        )
        assigned = res.rowcount

        # 2. Insert новых
        existing_res = await session.execute(
            select(TrackCode.track_code).where(TrackCode.track_code.in_(unique_codes))
        )
        existing_set = {row[0] for row in existing_res.all()}

        to_create = [
            TrackCode(track_code=c, status=DEFAULT_TRACK_STATUS, tg_id=user_tg_id)
            for c in unique_codes if c not in existing_set
        ]

        if to_create:
            session.add_all(to_create)

        await session.commit()
        return {"assigned": assigned, "created": len(to_create)}


async def add_multiple_track_codes(track_codes: List[str], tg_id: int) -> Tuple[int, List[str]]:
    """
    Добавляет список трек-кодов, если они еще не существуют (клиентская логика для множественного ввода).
    Оптимизирована до двух запросов (SELECT + INSERT).
    """
    if not track_codes:
        return 0, []

    unique_codes = list(set(track_codes))
    new_codes_added_count = 0
    added_codes: List[str] = []

    async with async_session() as session:
        # 1. Находим все существующие коды
        existing_res = await session.execute(
            select(TrackCode.track_code).where(TrackCode.track_code.in_(unique_codes))
        )
        existing_set = {row[0] for row in existing_res.all()}

        # 2. Формируем список новых объектов для добавления
        to_create = []
        for code in unique_codes:
            if code not in existing_set:
                new_track = TrackCode(
                    track_code=code,
                    status=DEFAULT_TRACK_STATUS,
                    tg_id=tg_id
                )
                to_create.append(new_track)
                added_codes.append(code)

        # 3. Массовая вставка
        if to_create:
            session.add_all(to_create)
            new_codes_added_count = len(to_create)
            await session.commit()

        return new_codes_added_count, added_codes


# --- АДМИНИСТРИРОВАНИЕ (DELETE / DROP) ---

async def delete_multiple_track_codes(track_codes: List[str]) -> int:
    """Массово удаляет список кодов по номеру."""
    if not track_codes: return 0
    async with async_session() as session:
        res = await session.execute(
            delete(TrackCode).where(TrackCode.track_code.in_(track_codes))
        )
        await session.commit()
        return res.rowcount


async def drop_track_codes_table():
    """Удаляет таблицу целиком (ОПАСНО)."""
    async with engine.begin() as conn:
        await conn.run_sync(TrackCode.__table__.drop)
