"""Модуль для загрузки конфигурации и реализации фильтров для бота."""

from os import getenv
from functools import lru_cache
from logging import getLogger

from aiogram.filters import BaseFilter
from aiogram.types import Message
from dotenv import load_dotenv

logger = getLogger(__name__)

# Загрузка конфигурации из .env
load_dotenv()
TELEGRAM_BOT_TOKEN = getenv('BOT_TOKEN')
DATABASE_URL = getenv('DATABASE_URL')
admin_ids_str = getenv('admin_ids')

# Проверка наличия переменных
if not all([TELEGRAM_BOT_TOKEN, DATABASE_URL, admin_ids_str]):
    logger.critical("Отсутствуют необходимые переменные окружения в .env (BOT_TOKEN, DATABASE_URL, admin_ids)")
    raise ValueError("Не удалось загрузить конфигурацию из .env")

admin_ids = list(map(int, admin_ids_str.split(",")))


class IsAdmin(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором."""

    def __init__(self, admin_ids: list[int]):
        """Инициализирует фильтр списком ID администраторов."""
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return is_admin_cached(message.from_user.id)


@lru_cache(maxsize=1000)
def is_admin_cached(user_id: int) -> bool:
    """Проверяет, входит ли пользователь в список администраторов (с кэшированием)."""
    return user_id in admin_ids
