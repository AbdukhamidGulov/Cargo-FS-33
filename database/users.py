from logging import getLogger
from aiocache import cached
from sqlalchemy import select, update, BigInteger, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column
from .base import async_session, Base, engine

logger = getLogger(__name__)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    username: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    phone: Mapped[str] = mapped_column(VARCHAR(20), nullable=True)

    def to_dict(self) -> dict:
        """Преобразует объект пользователя в словарь."""
        return {
            "id": self.id,
            "tg_id": self.tg_id,
            "name": self.name,
            "username": self.username,
            "phone": self.phone
        }


async def drop_users_table():
    """Удаляет таблицу users из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.tables['users'].drop(sync_conn))


async def add_user_info(tg_id: int, username: str, name: str, phone: str = None) -> dict:
    """Добавляет нового пользователя в таблицу users с указанными данными."""
    async with async_session() as session:
        async with session.begin():
            user = User(tg_id=tg_id, username=username, name=name, phone=phone)
            session.add(user)
            await session.commit()
            return user.to_dict()


@cached(ttl=300)  # Кэш на 5 минут
async def get_user_by_tg_id(tg_id: int):
    """Возвращает ID пользователя из таблицы users по его Telegram ID."""
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def get_users_tg_info() -> dict:
    """Возвращает словарь с Telegram ID и usernames всех пользователей."""
    async with async_session() as session:
        result = await session.execute(select(User.tg_id, User.username))
        return {row.tg_id: row.username for row in result}


async def get_info_profile(tg_id: int):
    """Возвращает полную информацию о пользователе по его Telegram ID."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None


async def update_user_info(tg_id: int, field: str, value: str) -> None:
    """Обновляет указанное поле пользователя в таблице users по его Telegram ID."""
    allowed_fields = {'name', 'username', 'phone'}
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле: {field}")

    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_id == tg_id).values(**{field: value})
        )
        await session.commit()


async def get_user_by_id(user_id: int):
    """Возвращает информацию о пользователе по его ID (с префиксом FS или без)."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None


async def update_user_by_internal_id(internal_id: int, **kwargs) -> bool:
    """
    Обновляет данные пользователя по его внутреннему ID (primary key).
    Принимает именованные аргументы (например, username="test", phone="123").
    """
    if not kwargs:
        return False

    async with async_session() as session:
        try:
            stmt = update(User).where(User.id == internal_id).values(**kwargs)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0  # Возвращает True, если строка была обновлена
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя по ID {internal_id}: {e}")
            await session.rollback()
            return False
