from logging import getLogger
from typing import Optional, Union

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

logger = getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


async def extract_text_from_message(message: Message, bot: Bot) -> Optional[str]:
    if message.document:
        try:
            file_info = await bot.get_file(message.document.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)

            # Читаем и декодируем байты
            return downloaded_file.read().decode('utf-8').strip()

        except UnicodeDecodeError:
            logger.warning(f"Файл от {message.from_user.id} не UTF-8")
            await message.answer("Ошибка: Файл должен быть в кодировке UTF-8.")
            return None
        except Exception as e:
            logger.error(f"Ошибка чтения файла от {message.from_user.id}: {e}")
            await message.answer("Произошла ошибка при чтении файла.")
            return None

    elif message.text:
        return message.text.strip()

    return None


async def send_chunked_response(target: Union[Message, CallbackQuery], text: str):
    message = target.message if isinstance(target, CallbackQuery) else target

    if not message:
        return

    if len(text) <= MAX_MESSAGE_LENGTH:
        await message.answer(text)
        return

    lines = text.splitlines()
    current_chunk = []
    current_length = 0

    for line in lines:
        line_len = len(line) + 1  # Учитываем перенос строки

        if current_length + line_len > MAX_MESSAGE_LENGTH:
            await message.answer("\n".join(current_chunk))
            current_chunk = [line]
            current_length = line_len
        else:
            current_chunk.append(line)
            current_length += line_len

    if current_chunk:
        await message.answer("\n".join(current_chunk))
