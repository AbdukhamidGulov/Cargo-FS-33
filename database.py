from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import String, select, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from filters_and_config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tg_id": self.tg_id,
            "name": self.name,
            "username": self.username,
            "phone": self.phone
        }

class TrackCode(Base):
    __tablename__ = 'track_codes'
    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(String(50))
    tg_id: Mapped[int] = mapped_column(nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "track_code": self.track_code,
            "status": self.status,
            "tg_id": self.tg_id,
        }


# Функция для создания и удаения таблиц
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_users_table():
    """Создание таблицы пользователей"""
    await create_tables() # Используем общую функцию для создания таблиц


async def drop_users_table():
    """Удаление таблицы пользователей"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.tables['users'].drop, args=(conn,))


async def drop_track_codes_table():
    """Удаление таблицы трек-кодов"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.tables['track_codes'].drop, args=(conn,))


# --- Функции для работы с пользователями ---
async def add_user_info(tg_id, username, name, phone=None):
    async with async_session() as session:
        user = User(tg_id=tg_id, username=username, name=name, phone=phone)
        session.add(user)
        await session.commit()
        return await get_user_by_tg_id(tg_id)


async def get_user_by_tg_id(tg_id: int):
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def get_users_tg_info():
    async with async_session() as session:
        result = await session.execute(select(User.tg_id, User.username))
        return {row.tg_id: row.username for row in result}


async def get_info_profile(tg_id) -> dict:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None


async def update_user_info(tg_id: int, field: str, value: str):
    allowed_fields = {'name', 'username', 'phone'}
    if field not in allowed_fields:
        raise ValueError(f"Invalid field: {field}")

    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.tg_id == tg_id)
            .values(**{field: value})
        )
        await session.commit()


async def get_user_by_id(user_id: str) -> dict | None:
    if user_id.startswith("FS"):
        user_id = int(user_id[2:])
    else:
        user_id = int(user_id)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None


# Операции с трек-кодами
async def get_track_codes_list():
    async with async_session() as session:
        result = await session.execute(select(TrackCode))
        return [{
            "id": tc.id,
            "track_code": tc.track_code,
            "status": tc.status,
            "tg_id": tc.tg_id
        } for tc in result.scalars()]


async def get_user_track_codes(tg_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.tg_id == tg_id)
        )
        return [(row.track_code, row.status) for row in result]


async def add_or_update_track_codes_list(track_codes: list[str], status: str, bot, message):
    async with async_session() as session:
        for track in track_codes:
            async with session.begin(): # Используем begin() для атомарности каждой операции
                # Попытка найти существующий трек-код
                stmt_select = select(TrackCode).filter_by(track_code=track)
                result = await session.execute(stmt_select)
                existing_track_code = result.scalar_one_or_none()

                if existing_track_code:
                    # Обновление существующего трек-кода
                    existing_track_code.status = status
                    tg_id_to_notify = existing_track_code.tg_id # Запоминаем tg_id для уведомления, если есть

                else:
                    # Создание нового трек-кода
                    new_track_code = TrackCode(track_code=track, status=status, tg_id=None)
                    session.add(new_track_code)
                    tg_id_to_notify = None # Нет tg_id для уведомления, так как код новый

            if existing_track_code and existing_track_code.tg_id:
                track_code_val = existing_track_code.track_code
                tg_id_val = existing_track_code.tg_id
                status_val = existing_track_code.status
                status_text = "на складе" if status_val == "in_stock" else "отправлен"
                try:
                    await bot.send_message(tg_id_val, f"Ваш товар с трек-кодом <code>{track_code_val}</code> {status_text}.")
                except TelegramBadRequest as e:
                    if "chat not found" in str(e):
                        bot.send_message(message.from_user.id, f"Не удалось отправить сообщение пользователю {tg_id_val}: {e}")
                        # Обновление tg_id на NULL, если чат не найден
                        async with session.begin():
                            stmt_update_tg_id = update(TrackCode).where(TrackCode.track_code == track_code_val, TrackCode.tg_id == tg_id_val).values(tg_id=None)
                            await session.execute(stmt_update_tg_id)
                    else:
                        bot.send_message(message.from_user.id, f"Ошибка при отправке сообщения: {e}")
                except Exception as e:
                    bot.send_message(message.from_user.id, f"Неизвестная ошибка при отправке сообщения: {e}")


async def check_or_add_track_code(track_code: str, tg_id: int, bot):
    async with async_session() as session:
        async with session.begin():
            stmt = select(TrackCode).filter_by(track_code=track_code)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row:
                old_status = row.status
                if row.tg_id is None:
                    row.tg_id = tg_id # Присваиваем tg_id напрямую объекту

                if old_status != "in_stock" and old_status != "shipped":
                    status = "in_stock" if row.status == "in_stock" else "shipped"
                    row.status = status # Обновляем статус напрямую объекту

                    # Отправка уведомления
                    if row.tg_id:
                        status_message = "Ваш товар уже на складе." if status == "in_stock" else "Ваш товар уже был отправлен."
                        await bot.send_message(row.tg_id, status_message)
                return row.status
            else:
                new_track_code = TrackCode(track_code=track_code, status="out_of_stock", tg_id=tg_id)
                session.add(new_track_code)
                return "out_of_stock"


async def delete_shipped_track_codes():
    async with async_session() as session:
        await session.execute(delete(TrackCode).where(TrackCode.status == 'shipped'))
        await session.commit()