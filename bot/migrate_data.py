from asyncio import run
from aiogram import Bot
from database.base import setup_database
from database.info_content import update_info_content
from filters_and_config import TELEGRAM_BOT_TOKEN
from text_info import *

async def migrate():
    """Переносит данные из text_info.py в базу данных info_content."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)  # Инициализация бота не обязательна, но может потребоваться некоторым функциям
    await setup_database()  # Инициализация подключения к базе данных

    data = {
        "main_menu_photo": main_menu_photo,
        "warehouse_address": warehouse_address,
        "sample_1688": sample_1688,
        "sample_Taobao": sample_Taobao,
        "sample_Pinduoduo": sample_Pinduoduo,
        "sample_Poizon": sample_Poizon,
        "order_form": order_form,
        "track_code_1688_photo1": track_code_1688_photo1,
        "track_code_1688_photo2": track_code_1688_photo2,
        "track_code_Taobao_photo1": track_code_Taobao_photo1,
        "track_code_Taobao_photo2": track_code_Taobao_photo2,
        "track_code_Pinduoduo_photo1": track_code_Pinduoduo_photo1,
        "track_code_Pinduoduo_photo2": track_code_Pinduoduo_photo2,
        "track_code_Poizon_photo1": track_code_Poizon_photo1,
        "track_code_Poizon_photo2": track_code_Poizon_photo2,
        "calculate_volume_photo": calculate_volume_photo1,
        "calculate_volume_photo_end": calculate_volume_photo5,
        "self_purchase": self_purchase,
        "tariffs_text": tariffs_text,
        "tariffs_document": tariffs_document,
        "goods_check_video1": goods_check_video1,
        "goods_check_photo1": goods_check_photo1,
        "goods_check_video2": goods_check_video2,
        "goods_check_photo2": goods_check_photo2,
        "goods_check_photo3": goods_check_photo3,
        "goods_check_text": goods_check_text,
        "consolidation_photo": consolidation_photo,
        "consolidation_text": consolidation_text,
        "forbidden_goods": forbidden_goods,
        "packing_photo": packing_photo,
        "packing_text": packing_text,
        "prices_document": prices_document,
        "prices_text": prices_text,
        "blank_text": blank_text,
    }

    for key, value in data.items():
        try:
            await update_info_content(key, value)
            print(f"Сохранено в базе данных: {key}")
        except Exception as e:
            print(f"Ошибка при сохранении {key}: {e}")
    await bot.session.close() # Закрываем сессию бота

if __name__ == "__main__":
    run(migrate())