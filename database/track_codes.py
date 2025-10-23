from logging import getLogger
from typing import Optional, List, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete, BigInteger, update, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import async_session, Base, engine
from .users import get_user_by_id

logger = getLogger(__name__)

# Статус по умолчанию для нового трек-кода
# Согласуется с логикой в check_or_add_track_code
DEFAULT_TRACK_STATUS = "out_of_stock"


class TrackCode(Base):
    __tablename__ = 'track_codes'
    id: Mapped[int] = mapped_column(primary_key=True)
    track_code: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String)
    tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def __repr__(self):
        return f"TrackCode(id={self.id}, code={self.track_code}, status={self.status}, tg_id={self.tg_id})"


# ************************************************
# НОВЫЙ ФУНКЦИОНАЛ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ************************************************

async def get_track_code_status(track_code: str) -> Optional[dict]:
    """
    Ищет трек-код в базе и возвращает его статус.
    Используется для проверки статуса пользователем.

    Исправлена типизация возвращаемого значения для совместимости.
    """
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status, TrackCode.tg_id)
            .where(TrackCode.track_code == track_code)
        )
        row = result.one_or_none()

        if row:
            # Преобразуем Row в словарь, включая статус и tg_id (если есть)
            # RowProxy ключи TrackCode.track_code, TrackCode.status, TrackCode.tg_id
            # Используем dict(row._mapping) или аналогичный подход для преобразования
            return {
                'track_code': row[0],
                'status': row[1],
                'tg_id': row[2]
            }
        return None


async def add_multiple_track_codes(track_codes: List[str], tg_id: int) -> Tuple[int, List[str]]:
    """
    Добавляет список трек-кодов в базу данных, если они еще не существуют.
    Новым кодам присваивается DEFAULT_TRACK_STATUS и tg_id пользователя.

    Обновлено: Возвращает кортеж (количество добавленных, список добавленных кодов).
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
                added_codes.append(track_code)  # Добавляем код в список

        await session.commit()
        return new_codes_added_count, added_codes  # Обновленное возвращаемое значение


# ************************************************
# СУЩЕСТВУЮЩИЕ ФУНКЦИИ
# ************************************************

async def drop_track_codes_table():
    """Удаляет таблицу track_codes из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[TrackCode.__table__])


async def get_track_codes_list() -> List[dict]:
    """Возвращает список всех трек-кодов с их статусами и Telegram ID."""
    async with async_session() as session:
        result = await session.execute(select(TrackCode))
        return [{
            "id": tc.id,
            "track_code": tc.track_code,
            "status": tc.status,
            "tg_id": tc.tg_id
        } for tc in result.scalars()]


async def get_user_track_codes(tg_id: int) -> List[Tuple[str, str]]:
    """Возвращает список трек-кодов и их статусов для указанного пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status)
            .where(TrackCode.tg_id == tg_id)
        )
        return result.all()


async def add_or_update_track_codes_list(codes_data: List[Tuple[str, Optional[int]]], status: str, bot: Bot) -> None:
    """
    Добавляет или обновляет список трек-кодов в базе данных и отправляет уведомления.
    Принимает список кортежей (track_code: str, user_internal_id_from_input: Optional[int]).
    """
    async with async_session() as session:
        for track_code, user_internal_id_from_input in codes_data:  # Переименовал переменную для ясности
            query_result = await session.execute(
                select(TrackCode).where(TrackCode.track_code == track_code)
            )
            existing = query_result.scalar_one_or_none()

            tg_id_for_notification = None  # Изначально нет ID для уведомления

            # *********** НАЧАЛО ИЗМЕНЕНИЙ ***********
            # Получаем реальный Telegram ID по внутреннему ID пользователя, если он есть
            actual_tg_id_from_internal_id = None
            if user_internal_id_from_input is not None:
                user_info = await get_user_by_id(user_internal_id_from_input)
                if user_info and 'tg_id' in user_info:
                    actual_tg_id_from_internal_id = user_info['tg_id']
                    logger.debug(
                        f"Найден TG ID {actual_tg_id_from_internal_id} для внутреннего ID {user_internal_id_from_input}")
                else:
                    logger.warning(
                        f"Не удалось найти TG ID для внутреннего ID пользователя: {user_internal_id_from_input} для трек-кода {track_code}. Уведомление не будет отправлено по этому ID.")
            # *********** КОНЕЦ ИЗМЕНЕНИЙ ***********

            if existing:
                existing.status = status
                # Если статус "arrived" и у нас есть актуальный TG ID из внутреннего ID
                if status == "arrived" and actual_tg_id_from_internal_id is not None:
                    # ОБНОВЛЯЕМ tg_id В БАЗЕ НА ПОЛУЧЕННЫЙ АКТУАЛЬНЫЙ TG ID
                    existing.tg_id = actual_tg_id_from_internal_id
                # Если статус не "arrived" или actual_tg_id_from_internal_id был None,
                # existing.tg_id остается как есть (либо уже был, либо None).
                # Это сохраняет привязку, если пользователь сам отслеживал.

                # TG ID для уведомления берется из существующей записи (возможно, обновленной)
                tg_id_for_notification = existing.tg_id
            else:
                # Если трек-код не существует, создаем новую запись
                new_track_code = TrackCode(track_code=track_code, status=status)

                # Для 'arrived' статуса используем найденный TG ID
                if status == "arrived":
                    new_track_code.tg_id = actual_tg_id_from_internal_id
                    tg_id_for_notification = actual_tg_id_from_internal_id
                else:
                    # Для 'in_stock' или 'shipped' (новой записи) tg_id в базе будет None
                    new_track_code.tg_id = None
                    tg_id_for_notification = None  # Уведомление не отправляется для новых кодов без ID
                session.add(new_track_code)

            # Отправляем уведомление, если tg_id для него определен и не None
            if tg_id_for_notification is not None:
                await safe_send_notification(bot, track_code, tg_id_for_notification, status, session)
        await session.commit()


async def safe_send_notification(bot: Bot, track_code: str, chat_id: int, status: str, session) -> bool:
    """Безопасно отправляет уведомление пользователю и обновляет tg_id на None при ошибке."""
    if not chat_id:
        return False

    notification_text = ""
    if status == "in_stock":
        notification_text = f"Ваш товар с трек-кодом <code>{track_code}</code> <b>прибыл на склад</b>."
    elif status == "shipped":
        notification_text = f"Ваш товар с трек-кодом <code>{track_code}</code> <b>отправлен</b>."
    elif status == "arrived":
        notification_text = (
            f"Ваш товар с трек-кодом <code>{track_code}</code> <b>прибыл на место назначения</b>.\n\n"
            "Пожалуйста, свяжитесь с главным администратором для получения товара: @fir2201"
        )
    else:
        logger.warning(f"Неизвестный статус для уведомления: {status}")
        return False

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=notification_text
        )
        logger.debug(
            f"Уведомление отправлено пользователю {chat_id} для трек-кода {track_code} со статусом '{status}'.")
        return True
    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower() or "blocked" in str(e).lower():
            logger.warning(
                f"Не удалось отправить уведомление: чат {chat_id} не найден или бот заблокирован. Для трек-кода {track_code} tg_id будет обнулен.")
            await session.execute(
                update(TrackCode).where(TrackCode.track_code == track_code).values(tg_id=None)
            )
            # Примечание: в этой функции session.commit() не нужен, т.к. это в рамках общей сессии add_or_update_track_codes_list
        else:
            logger.error(f"Ошибка Telegram API для {chat_id} (трек-код {track_code}, статус {status}): {e}")
        return False
    except Exception as e:
        logger.error(
            f"Неизвестная ошибка при отправке уведомления пользователю {chat_id} (трек-код {track_code}, статус {status}): {e}")
        return False


async def check_or_add_track_code(track_code: str, tg_id: int) -> str:
    """Оптимизированная проверка/добавление трек-кода."""
    async with async_session() as session:
        async with session.begin():
            stmt = select(TrackCode).where(TrackCode.track_code == track_code).with_for_update()
            query_result = await session.execute(stmt)
            tc = query_result.scalar_one_or_none()

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
