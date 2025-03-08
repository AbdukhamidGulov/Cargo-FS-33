from os import getenv
from typing import Any
from functools import lru_cache

from aiogram.filters import BaseFilter
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_BOT_TOKEN = getenv('BOT_TOKEN')
admin_ids = list(map(int, getenv('admin_ids').split(",")))


class IsAdmin(BaseFilter):
    def __init__(self, adm_ids: list[int]):
        self.admin_ids = adm_ids

    async def __call__(self, message: Message, **kwargs: Any) -> bool:
        return is_admin_cached(message.from_user.id)

# Кэшируем проверку прав (1000 последних вызовов)
@lru_cache(maxsize=1000)
def is_admin_cached(user_id: int) -> bool:
    return user_id in admin_ids
