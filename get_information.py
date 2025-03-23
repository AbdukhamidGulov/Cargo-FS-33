from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram import F, Router

from text_info import *
from database.users import get_info_profile, get_user_by_tg_id
from keyboards import main_keyboard, where_get_keyboard, reg_keyboard, create_samples_keyboard

get_info = Router()


# ВСЯ ОБРАБОТКА ДЛЯ АДРЕСА СКЛАДА И ОБРАЗЦОВ
@get_info.callback_query(F.data == "warehouse_address")
async def address(callback: CallbackQuery):
    """Отправляет адрес склада пользователю."""
    id_from_user = await get_user_by_tg_id(callback.from_user.id)
    if not id_from_user:
        await callback.answer(
            "❌ Вы не зарегистрированы!\n\nХотите зарегистрироваться?", reply_markup=reg_keyboard)
        return
    fs = f"{id_from_user:04d}"
    await callback.message.answer(warehouse_address.format(fs))
    await callback.message.answer("Нажмите чтобы увидеть образцы", reply_markup=create_samples_keyboard())

@get_info.callback_query(F.data.startswith("simple_"))
async def handle_simple(callback: CallbackQuery):
    """Обрабатывает запрос на отображение образца."""
    await callback.message.delete()
    samples = {
        "1688": {"photo_id": sample_1688, "caption": "Образец 1688"},
        "Taobao": {"photo_id": sample_Taobao, "caption": "Образец Taobao"},
        "Pinduoduo": {"photo_id": sample_Pinduoduo, "caption": "Образец Pinduoduo"},
        "Poizon": {"photo_id": sample_Poizon, "caption": "Образец poizon"}
    }

    key = callback.data.split("_")[-1]
    sample = samples[key]
    samples_keyboard = create_samples_keyboard(key)
    if sample:
        await callback.message.answer_photo(sample["photo_id"], sample["caption"])
        await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=samples_keyboard)
    else:
        await callback.message.answer("Образец не найден.")


# Другие обработчики
@get_info.message(F.text == "Бланк для заказа")
async def send_order_form(message: Message):
    """Отправляет бланк для заказа."""
    await message.answer(blank_info)
    await message.answer_document(document=order_form, caption="Вот ваш бланк для заказа. Заполните его и отправьте нам!")


@get_info.message(F.text == "Где брать трек-номер")
async def send_track_number_info(message: Message):
    """Запрашивает у пользователя выбор сайта для получения информации о трек-номерах."""
    await message.answer('⬇️ <b>С какого сайта вы хотите получить информацию о получении трек-номеров?</b>',
                         reply_markup=where_get_keyboard)

@get_info.callback_query(F.data.startswith("where_get_with_"))
async def handle_simple(callback: CallbackQuery):
    """Отправляет фото с информацией о трек-номерах для выбранного сайта."""
    photos = {
        "1688": [track_number_info_photo1_1688, track_number_info_photo2_1688],
        "Taobao": [track_number_info_photo1_Taobao, track_number_info_photo2_Taobao],
        "Pinduoduo": [track_number_info_photo1_Pinduoduo, track_number_info_photo2_Pinduoduo],
        "Poizon": [track_number_info_photo1_Poizon, track_number_info_photo2_Poizon]
    }

    key = callback.data.split("_")[-1]
    photo_key = photos.get(key)
    if photo_key:
        media = [InputMediaPhoto(media=photo_key[0], caption=key),
                 InputMediaPhoto(media=photo_key[1])]
        await callback.message.answer_media_group(media)
    else:
        await callback.message.answer("Информация о трек-номерах не найдена.")


@get_info.message(F.text == "Тарифы")
async def send_tariffs(message: Message):
    """Отправляет информацию о тарифах."""
    await message.answer(tariffs)


@get_info.message(F.text == "Проверка товаров")
async def send_goods_check(message: Message):
    """Отправляет медиа и текст о проверке товаров."""
    media = [InputMediaVideo(media=goods_check_video1),
        InputMediaPhoto(media=goods_check_photo1),
        InputMediaVideo(media=goods_check_video2),
        InputMediaPhoto(media=goods_check_photo2),
        InputMediaPhoto(media=goods_check_photo3)]
    await message.answer_media_group(media)
    await message.reply(goods_check, reply_markup=main_keyboard)


@get_info.message(F.text == "Консолидация")
async def send_consolidation(message: Message):
    """Отправляет фото и текст о консолидации."""
    inf = await get_info_profile(message.from_user.id)
    if not inf:
        await message.answer("Профиль не найден.")
        return
    await message.answer_photo(consolidation_photo, consolidation.format(f'<code>FS{inf.get('id'):04d}</code>'),
                               show_caption_above_media=True)


@get_info.message(F.text == "Запрещённые товары")
async def send_forbidden_goods(message: Message):
    """Отправляет информацию о запрещённых товарах."""
    await message.answer(forbidden_goods)


@get_info.message(F.text == "Упаковка")
async def send_packing(message: Message):
    """Отправляет фото и текст об упаковке."""
    await message.answer_photo(packing_photo, packing)


@get_info.message(F.text == "️Цены")  # Нету кнопки
async def send_prices(message: Message):
    """Отправляет информацию о ценах."""
    await message.answer_photo(prices_photo, prices)


# ОБРАБОТЧИК КОМАНДЫ НАЗАД В ГЛАВНОЕ МЕНЮ
@get_info.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    """"""
    await callback.message.delete()
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)
