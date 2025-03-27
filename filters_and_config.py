"""Модуль для загрузки конфигурации и реализации фильтров для бота."""

from os import getenv
from typing import Any
from functools import lru_cache
from logging import getLogger

from aiogram.filters import BaseFilter
from aiogram.types import Message
from dotenv import load_dotenv

logger = getLogger(__name__)

# Загрузка конфигурации из .env
load_dotenv()


try:
    TELEGRAM_BOT_TOKEN = getenv('BOT_TOKEN')
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Не задан BOT_TOKEN в .env")

    DATABASE_URL = getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("Не задан DATABASE_URL в .env")

    admin_ids_str = getenv('ADMIN_IDS')
    if not admin_ids_str:
        raise ValueError("Не задан admin_ids в .env")

    admin_ids = list(map(int, admin_ids_str.split(",")))
    logger.info(f"Загружены ID администраторов: {admin_ids}")

except ValueError as e:
    logger.critical(f"Ошибка загрузки конфигурации: {e}")
    raise

class IsAdmin(BaseFilter):
    """Фильтр для проверки администратора (совместимый вариант)."""

    def __init__(self, adm_ids: list[int]):
        self.admin_ids = adm_ids

    async def __call__(self, message: Message, **kwargs: Any) -> bool:
        try:
            return is_admin_cached(message.from_user.id)
        except Exception as ex:
            logger.error(f"Ошибка проверки прав администратора: {ex}")
            return False

@lru_cache(maxsize=1000)
def is_admin_cached(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором (с кэшированием)."""
    return user_id in admin_ids