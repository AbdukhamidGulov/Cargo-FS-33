from logging import getLogger
from aiocache import cached
from sqlalchemy import select, update, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from .base import async_session, Base, engine

logger = getLogger(__name__)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)

    def to_dict(self) -> dict:
        """
        Преобразует объект пользователя в словарь.

        Returns:
            dict: Словарь с данными пользователя (id, tg_id, name, username, phone).
        """
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
    """
    Добавляет нового пользователя в таблицу users с указанными данными.

    Args:
        tg_id (int): Telegram ID пользователя.
        username (str): Имя пользователя в Telegram.
        name (str): Полное имя пользователя.
        phone (str, optional): Номер телефона пользователя. По умолчанию None.

    Returns:
        dict: Словарь с данными пользователя (id, tg_id, name, username, phone).

    Raises:
        Exception: Если произошла ошибка при добавлении пользователя в базу данных.
    """
    async with async_session() as session:
        try:
            async with session.begin():
                user = User(tg_id=tg_id, username=username, name=name, phone=phone)
                session.add(user)
                await session.commit()
                return user.to_dict()
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя с tg_id={tg_id}: {e}")
            raise

@cached(ttl=300)  # Кэш на 5 минут
async def get_user_by_tg_id(tg_id: int) -> int | None:
    """
    Возвращает ID пользователя из таблицы users по его Telegram ID.

    Args:
        tg_id (int): Telegram ID пользователя.

    Returns:
        int | None: ID пользователя в базе данных или None, если пользователь не найден.

    Raises:
        Exception: Если произошла ошибка при запросе к базе данных.
    """
    async with async_session() as session:
        try:
            result = await session.execute(select(User.id).where(User.tg_id == tg_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя с tg_id={tg_id}: {e}")
            raise

async def get_users_tg_info() -> dict:
    """
    Возвращает словарь с Telegram ID и usernames всех пользователей.

    Returns:
        dict: Словарь, где ключи — Telegram ID, значения — usernames.

    Raises:
        Exception: Если произошла ошибка при запросе к базе данных.
    """
    async with async_session() as session:
        try:
            result = await session.execute(select(User.tg_id, User.username))
            return {row.tg_id: row.username for row in result}
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователях: {e}")
            raise

async def get_info_profile(tg_id: int) -> dict | None:
    """
    Возвращает полную информацию о пользователе по его Telegram ID.

    Args:
        tg_id (int): Telegram ID пользователя.

    Returns:
        dict | None: Словарь с данными пользователя или None, если пользователь не найден.

    Raises:
        Exception: Если произошла ошибка при запросе к базе данных.
    """
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.tg_id == tg_id))
            user = result.scalar_one_or_none()
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Ошибка при получении профиля с tg_id={tg_id}: {e}")
            raise

async def update_user_info(tg_id: int, field: str, value: str) -> None:
    """
    Обновляет указанное поле пользователя в таблице users по его Telegram ID.

    Args:
        tg_id (int): Telegram ID пользователя.
        field (str): Поле для обновления (name, username или phone).
        value (str): Новое значение поля.

    Raises:
        ValueError: Если указано недопустимое поле.
        Exception: Если произошла ошибка при обновлении данных.
    """
    allowed_fields = {'name', 'username', 'phone'}
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле: {field}")

    async with async_session() as session:
        try:
            await session.execute(
                update(User).where(User.tg_id == tg_id).values(**{field: value})
            )
            await session.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении поля {field} для tg_id={tg_id}: {e}")
            raise

async def get_user_by_id(user_id: str) -> dict | None:
    """
    Возвращает информацию о пользователе по его ID (с префиксом FS или без).

    Args:
        user_id (str): ID пользователя, может быть с префиксом FS.

    Returns:
        dict | None: Словарь с данными пользователя или None, если пользователь не найден.

    Raises:
        ValueError: Если user_id не является числом или строкой с префиксом FS.
        Exception: Если произошла ошибка при запросе к базе данных.
    """
    try:
        if user_id.startswith("FS"):
            user_id = int(user_id[2:])
        else:
            user_id = int(user_id)
    except ValueError:
        raise ValueError("Недопустимый формат user_id. Должен быть числом или строкой с префиксом 'FS'.")

    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя с id={user_id}: {e}")
            raise
