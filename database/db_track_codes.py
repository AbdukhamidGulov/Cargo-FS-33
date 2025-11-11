from logging import getLogger
from typing import Optional, List, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete, BigInteger, update, String
from sqlalchemy.orm import Mapped, mapped_column

from .db_base import async_session, Base, engine
from .db_users import get_user_by_id

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


# ФУНКЦИЯ ДЛЯ ПОИСКА ВЛАДЕЛЬЦА ТРЕК-КОДА
async def get_track_code_info(track_code: str) -> Optional[dict]:
    """
    Ищет трек-код в базе данных и возвращает полную информацию о нем:
    трек-код, статус и TG ID владельца. Используется в админ-панели.
    """
    logger.debug(f"В файле database/track_codes.py - Поиск трек-кода: '{track_code}'")
    async with async_session() as session:
        result = await session.execute(
            select(TrackCode.track_code, TrackCode.status, TrackCode.tg_id)
            .where(TrackCode.track_code == track_code)
        )
        row = result.one_or_none()

        if row:
            logger.debug(f"В файле database/track_codes.py - Найден трек-код: {row[0]}, статус: {row[1]}, tg_id: {row[2]}")
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


# --- Административные и вспомогательные функции ---

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
        for track_code, user_internal_id_from_input in codes_data:
            logger.info(
                f"Обработка трек-кода: '{track_code}', внутренний ID: {user_internal_id_from_input}, статус: {status}")

            # Ищем существующий трек-код
            query_result = await session.execute(
                select(TrackCode).where(TrackCode.track_code == track_code)
            )
            existing = query_result.scalar_one_or_none()

            # Получаем реальный Telegram ID по внутреннему ID пользователя
            actual_tg_id_from_internal_id = None
            if user_internal_id_from_input is not None:
                user_info = await get_user_by_id(user_internal_id_from_input)
                if user_info and 'tg_id' in user_info:
                    actual_tg_id_from_internal_id = user_info['tg_id']
                    logger.info(
                        f"Найден TG ID {actual_tg_id_from_internal_id} для внутреннего ID {user_internal_id_from_input}")
                else:
                    logger.warning(
                        f"Не удалось найти TG ID для внутреннего ID пользователя: {user_internal_id_from_input}")

            if existing:
                logger.info(
                    f"Трек-код '{track_code}' существует. Старый статус: {existing.status}, старый TG ID: {existing.tg_id}")

                # Обновляем статус
                existing.status = status

                # ПРИВЯЗЫВАЕМ ВЛАДЕЛЬЦА В ЛЮБОМ СТАТУСЕ, если есть данные пользователя
                if actual_tg_id_from_internal_id is not None:
                    logger.info(
                        f"Обновляем TG ID для '{track_code}' с {existing.tg_id} на {actual_tg_id_from_internal_id}")
                    existing.tg_id = actual_tg_id_from_internal_id
                    tg_id_for_notification = actual_tg_id_from_internal_id
                else:
                    # Если нет нового TG ID, но есть старый - используем старый для уведомления
                    tg_id_for_notification = existing.tg_id
                    if existing.tg_id:
                        logger.info(f"Используем существующий TG ID {existing.tg_id} для уведомления")
                    else:
                        logger.warning(f"Трек-код '{track_code}' не привязан к пользователю")

            else:
                # Создаем новую запись
                logger.info(f"Создаем новый трек-код: '{track_code}'")
                new_track_code = TrackCode(track_code=track_code, status=status)

                # ПРИВЯЗЫВАЕМ ВЛАДЕЛЬЦА ПРИ СОЗДАНИИ В ЛЮБОМ СТАТУСЕ
                if actual_tg_id_from_internal_id is not None:
                    new_track_code.tg_id = actual_tg_id_from_internal_id
                    tg_id_for_notification = actual_tg_id_from_internal_id
                    logger.info(f"Новый трек-код '{track_code}' привязан к TG ID {actual_tg_id_from_internal_id}")
                else:
                    new_track_code.tg_id = None
                    tg_id_for_notification = None
                    logger.warning(f"Новый трек-код '{track_code}' создан без привязки к пользователю")

                session.add(new_track_code)

            # Отправляем уведомление если есть кому отправлять
            if tg_id_for_notification is not None:
                logger.info(f"Пытаемся отправить уведомление для '{track_code}' пользователю {tg_id_for_notification}")
                await safe_send_notification(bot, track_code, tg_id_for_notification, status, session)
            else:
                logger.warning(f"Нельзя отправить уведомление для '{track_code}' - нет TG ID пользователя")

        await session.commit()
        logger.info("Все изменения в трек-кодах сохранены в базу данных")


async def safe_send_notification(bot: Bot, track_code: str, chat_id: int, status: str, session) -> bool:
    """Безопасно отправляет уведомление пользователю и обновляет tg_id на None при ошибке, если чат недоступен."""
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
            # Обнуляем TG ID в базе данных, чтобы больше не пытаться отправить уведомление
            await session.execute(
                update(TrackCode).where(TrackCode.track_code == track_code).values(tg_id=None)
            )
        else:
            logger.error(f"Ошибка Telegram API для {chat_id} (трек-код {track_code}, статус {status}): {e}")
        return False
    except Exception as e:
        logger.error(
            f"Неизвестная ошибка при отправке уведомления пользователю {chat_id} (трек-код {track_code}, статус {status}): {e}")
        return False


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


async def bulk_assign_track_codes(track_codes: List[str], tg_id: int) -> Tuple[int, List[str]]:
    """
    Массово привязывает список трек-кодов к пользователю.
    Возвращает кортеж (количество успешных, список неудачных трек-кодов).
    """
    success_count = 0
    failed_codes = []

    async with async_session() as session:
        for track_code in track_codes:
            try:
                result = await session.execute(
                    select(TrackCode).where(TrackCode.track_code == track_code)
                )
                track = result.scalar_one_or_none()

                if track:
                    track.tg_id = tg_id
                    success_count += 1
                    logger.info(f"Трек-код {track_code} привязан к пользователю {tg_id}")
                else:
                    failed_codes.append(track_code)
                    logger.warning(f"Трек-код {track_code} не найден для привязки")

            except Exception as e:
                failed_codes.append(track_code)
                logger.error(f"Ошибка при привязке {track_code}: {e}")

        await session.commit()

    return success_count, failed_codes