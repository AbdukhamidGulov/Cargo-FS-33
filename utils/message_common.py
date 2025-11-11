from logging import getLogger
from typing import Union, Optional

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, InlineKeyboardMarkup

logger = getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram


async def extract_text_from_message(message: Message, bot: Bot) -> Optional[str]:
    """
    Извлекает текст из сообщения.
    Если это обычный текст - возвращает его.
    Если это документ (.txt) - скачивает и читает его содержимое.
    Возвращает None в случае ошибки или если тип сообщения не поддерживается.
    """
    if message.document:
        # Проверка на текстовый файл (опционально, но полезно)
        # Mime-type может быть разным для txt, лучше смотреть на расширение или пробовать читать
        try:
            file_id = message.document.file_id
            file_info = await bot.get_file(file_id)
            file_path = file_info.file_path

            # Скачиваем файл в память
            downloaded_file = await bot.download_file(file_path)

            # Пытаемся декодировать как UTF-8 текст
            content = downloaded_file.read().decode('utf-8')
            return content.strip()

        except UnicodeDecodeError:
            logger.warning(f"Файл от пользователя {message.from_user.id} не в кодировке UTF-8.")
            await message.answer("Ошибка: Файл должен быть в кодировке UTF-8.")
            return None
        except Exception as e:
            logger.error(f"Ошибка при чтении файла от {message.from_user.id}: {e}")
            await message.answer("Произошла ошибка при чтении файла.")
            return None

    elif message.text:
        return message.text.strip()

    else:
        return None


async def send_chunked_response(target: Union[Message, CallbackQuery], text: str):
    """
    Отправляет длинный текст, разбивая его на части по 4096 символов.
    Обрабатывает как объекты Message (от прямого ввода), так и CallbackQuery
    (от нажатия инлайн-кнопок), извлекая из них целевой Message для ответа.
    """
    LIMIT = 4096

    # Определяем целевой объект Message для отправки ответа
    if isinstance(target, CallbackQuery):
        # Если это CallbackQuery, используем исходное сообщение, к которому
        # была прикреплена кнопка (target.message)
        message = target.message
    else:
        # Иначе, это уже Message
        message = target

    if not message:
        # На случай, если message в CallbackQuery оказался None (редкий случай)
        return

    # Если текст короткий, отправляем его целиком
    if len(text) <= LIMIT:
        await message.answer(text)
        return

    # Разбиваем текст на чанки по строкам
    lines = text.splitlines()
    current_chunk = []
    current_length = 0

    for line in lines:
        # Длина строки + 1 символ для переноса строки
        line_len = len(line) + 1

        if current_length + line_len > LIMIT:
            # Отправляем текущий чанк
            await message.answer("\n".join(current_chunk))
            # Начинаем новый чанк с текущей строки
            current_chunk = [line]
            current_length = line_len
        else:
            current_chunk.append(line)
            current_length += line_len

    # Отправляем оставшийся чанк
    if current_chunk:
        await message.answer("\n".join(current_chunk))