from logging import getLogger

from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.track_codes import get_user_track_codes
from track_numbers import status_messages

track_code_search_router = Router()
logger = getLogger(__name__)



# ************************************************
# 3. ПРОСМОТР СВОИХ ТРЕК-КОДОВ (callback остается прежним)
# ************************************************

@track_code_search_router.callback_query(F.data == "my_track_codes")
async def my_track_codes(callback: CallbackQuery):
    """Отправляет пользователю список его трек-кодов."""
    await callback.message.delete()
    user_tg_id = callback.from_user.id
    track_codes = await get_user_track_codes(user_tg_id)

    if track_codes:
        response = "<b>Ваши отслеживаемые трек-коды:</b>\n\n"
        for my_track_code, status in track_codes:
            # Используем status_messages для получения более понятного статуса
            status_message = status_messages.get(status, "Неизвестный статус")
            response += f"• <code>{my_track_code}</code> - <i>{status_message}</i>\n"
        await callback.message.answer(response)
    else:
        await callback.message.answer(
            "У вас нет зарегистрированных трек-кодов.\n"
            "Чтобы добавить их, воспользуйтесь командой <code>Добавить трек-кода</code>."
        )


# я создал файл track_codes_search.py, создал роутер и добавил в mail.py в список роутеров и перенёсь этот часть кода, чтобы увеличит функционал этой функции. При поиске массовых трек кодов все пока что окай, если ты не можешь предложить что-то лучше
# Но когда ищет один трек код то нужно более подробное его оборажение

# В будущем нужно добавить возможность добавить имя трек-коду, даты поступления на склад, отправки из слада и поступлению в пункт выдачи


# В админ панели нужно добавить функцию удаление одного или многих трек-кодов
# В админ панели нужно добавить функцию поиска владелца трек-кода

# При добавление трек кодов админом, добавить что-то вроде Kafka, потому что при добавлении более 400 разом, часть не добавляется