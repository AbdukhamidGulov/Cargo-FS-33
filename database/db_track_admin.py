from logging import getLogger
from typing import Optional, List, Tuple, Set

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete, update

from .db_base import async_session, engine
from .db_users import get_user_by_id
from .db_track_codes import TrackCode

logger = getLogger(__name__)


# --- ОПЕРАЦИИ УДАЛЕНИЯ И СБРОСА ТАБЛИЦ ---

async def drop_track_codes_table():
    """Удаляет таблицу track_codes из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(TrackCode.metadata.drop_all, tables=[TrackCode.__table__])


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


async def bulk_delete_track_codes(track_codes: List[str]) -> Tuple[int, int]:
    """
    Массово удаляет список трек-кодов из базы данных.

    Возвращает кортеж (количество успешно удаленных, количество ненайденных кодов).
    """
    if not track_codes:
        return 0, 0

    # Преобразуем список в множество для быстрой проверки
    track_codes_set: Set[str] = set(track_codes)

    async with async_session() as session:
        # 1. Находим, какие коды из списка реально существуют
        result = await session.execute(
            select(TrackCode.track_code).where(TrackCode.track_code.in_(track_codes_set))
        )
        existing_codes_set = set(result.scalars().all())

        success_count = len(existing_codes_set)

        # 2. Вычисляем количество ненайденных кодов (ошибки удаления)
        failed_count = len(track_codes_set) - success_count

        if success_count > 0:
            # 3. Выполняем массовое удаление найденных кодов
            delete_result = await session.execute(
                delete(TrackCode)
                .where(TrackCode.track_code.in_(existing_codes_set))
            )
            actual_deleted_count = delete_result.rowcount
            await session.commit()

            # Возвращаем фактическое количество удаленных и количество ошибок
            return actual_deleted_count, failed_count

        return 0, failed_count


# --- ОПЕРАЦИИ ПОЛУЧЕНИЯ ДАННЫХ ---

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


# --- ОПЕРАЦИИ ОБНОВЛЕНИЯ И УВЕДОМЛЕНИЙ ---

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
