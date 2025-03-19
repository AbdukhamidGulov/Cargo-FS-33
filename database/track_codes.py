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
        """
        Преобразует объект трек-кода в словарь.

        Returns:
            dict: Словарь с данными трек-кода (id, track_code, status, tg_id).
        """
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
    """
    Возвращает список всех трек-кодов с их статусами и Telegram ID.

    Returns:
        list[dict]: Список словарей с данными трек-кодов.

    Raises:
        Exception: Если произошла ошибка при запросе к базе данных.
    """
    async with async_session() as session:
        try:
            result = await session.execute(select(TrackCode))
            return [tc.to_dict() for tc in result.scalars()]
        except Exception as e:
            logger.error(f"Ошибка при получении списка трек-кодов: {e}")
            raise

async def get_user_track_codes(tg_id: int) -> list[tuple]:
    """
    Возвращает список трек-кодов и их статусов для указанного пользователя.

    Args:
        tg_id (int): Telegram ID пользователя.

    Returns:
        list[tuple]: Список кортежей (track_code, status).

    Raises:
        Exception: Если произошла ошибка при запросе к базе данных.
    """
    async with async_session() as session:
        try:
            result = await session.execute(
                select(TrackCode.track_code, TrackCode.status).where(TrackCode.tg_id == tg_id)
            )
            return [(row.track_code, row.status) for row in result]
        except Exception as e:
            logger.error(f"Ошибка при получении трек-кодов для tg_id={tg_id}: {e}")
            raise

async def update_or_add_track_code(session, track_code: str, status: str) -> TrackCode:
    """
    Обновляет статус существующего трек-кода или добавляет новый.

    Args:
        session: Активная сессия базы данных.
        track_code (str): Трек-код.
        status (str): Новый статус трек-кода.

    Returns:
        TrackCode: Объект трек-кода.

    Raises:
        Exception: Если произошла ошибка при обновлении или добавлении трек-кода.
    """
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
    """
    Отправляет уведомление пользователю о статусе его трек-кода.

    Args:
        bot: Объект бота для отправки сообщений.
        track_code_obj (TrackCode): Объект трек-кода.
        message: Объект сообщения для ответа при ошибке.

    Raises:
        Exception: Если произошла ошибка при отправке сообщения.
    """
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
    """
    Добавляет или обновляет список трек-кодов с указанным статусом и отправляет уведомления.

    Args:
        track_codes (list[str]): Список трек-кодов.
        status (str): Новый статус для трек-кодов.
        bot: Объект бота для отправки уведомлений.
        message: Объект сообщения для ответа при ошибке.

    Raises:
        Exception: Если произошла ошибка при обновлении или добавлении трек-кодов.
    """
    async with async_session() as session:
        for track in track_codes:
            try:
                async with session.begin():
                    track_code_obj = await update_or_add_track_code(session, track, status)
                    await notify_user(bot, track_code_obj, message)
            except Exception as e:
                logger.error(f"Ошибка при обработке трек-кода {track}: {e}")
                raise

async def check_or_add_track_code(track_code: str, tg_id: int, bot) -> str:
    """
    Функция выполняет две задачи:
    1. Если трек-код уже есть в базе данных: возвращать его текущий статус и показывать пользователю соответствующее сообщение
    (например, "Ваш товар уже на складе", "Ваш товар ещё не прибыл на склад" или "Ваш товар был отправлен").

    2. Если трек-кода нет в базе: добавлять его со статусом "out_of_stock" и сообщать пользователю
    "Ваш товар ещё не прибыл на склад".



    Args:
        track_code (str): Трек-код.
        tg_id (int): Telegram ID пользователя.
        bot: Объект бота для отправки уведомлений.

    Returns:
        str: Текущий статус трек-кода.

    Raises:
        ValueError: Если track_code пустой или некорректный.
        Exception: Если произошла ошибка при проверке или добавлении трек-кода.
    """
    if not track_code or not isinstance(track_code, str):
        raise ValueError("Трек-код должен быть непустой строкой.")

    async with async_session() as session:
        try:
            async with session.begin():
                stmt = select(TrackCode).filter_by(track_code=track_code)
                result = await session.execute(stmt)
                track_code_obj = result.scalar_one_or_none()

                if track_code_obj:
                    # Обновляем tg_id, если он был None
                    if track_code_obj.tg_id is None:
                        track_code_obj.tg_id = tg_id
                        await session.commit()
                    # Просто возвращаем текущий статус без его изменения
                    return track_code_obj.status
                else:
                    # Добавляем новый трек-код со статусом "out_of_stock"
                    new_track_code = TrackCode(track_code=track_code, status="out_of_stock", tg_id=tg_id)
                    session.add(new_track_code)
                    await session.commit()
                    return "out_of_stock"
        except Exception as e:
            logger.error(f"Ошибка при проверке/добавлении трек-кода {track_code}: {e}")
            raise


async def delete_shipped_track_codes() -> None:
    """
    Удаляет все трек-коды со статусом 'shipped' из таблицы track_codes.

    Raises:
        Exception: Если произошла ошибка при удалении трек-кодов.
    """
    async with async_session() as session:
        try:
            await session.execute(delete(TrackCode).where(TrackCode.status == 'shipped'))
            await session.commit()
        except Exception as e:
            logger.error(f"Ошибка при удалении трек-кодов со статусом 'shipped': {e}")
            raise
