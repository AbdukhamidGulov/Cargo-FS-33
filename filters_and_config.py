from os import getenv

from aiogram.filters import BaseFilter
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = getenv('BOT_TOKEN')
admin_ids = list(map(int, getenv('admin_ids').split(",")))


class IsAdmin(BaseFilter):
    def __init__(self, adm_ids: list[int]):
        self.admin_ids = adm_ids

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids
