from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram import F, Router

from text_info import *
from database import get_info_profile, get_user_by_tg_id, get_user_track_codes
from keyboards import (my_profile_keyboard, samples_keyboard, samples_1688_keyboard, samples_Taobao_keyboard, \
                       samples_Pinduoduo_keyboard, samples_Poizon_keyboard, main_keyboard, change_data_keyboard,
                       main_inline_keyboard, where_get_keyboard)

get_info = Router()


# ВСЯ ОБРАБОТКА ДЛЯ АДРЕСА СКЛАДА И ОБРАЗЦОВ
@get_info.message(F.text == "️Адрес склада")
async def address(message: Message):
    user_id = await get_user_by_tg_id(message.from_user.id)
    fs = f"{user_id[0]:04d}"
    await message.answer(warehouse_address.format(fs))
    await message.answer("Нажмите чтобы увидеть образцы", reply_markup=samples_keyboard)

@get_info.callback_query(F.data.startswith("simple_"))
async def handle_simple(callback: CallbackQuery):
    await callback.message.delete()
    samples = {"1688": {"photo_id": sample_1688, "caption": "Образец 1688", "keyboard": samples_1688_keyboard},
        "Taobao": {"photo_id": sample_Taobao, "caption": "Образец Taobao", "keyboard": samples_Taobao_keyboard},
        "Pinduoduo": {"photo_id": sample_Pinduoduo, "caption": "Образец Pinduoduo", "keyboard": samples_Pinduoduo_keyboard},
        "Poizon": {"photo_id": sample_Poizon, "caption": "Образец poizon", "keyboard": samples_Poizon_keyboard}}

    key = callback.data.split("_")[-1]
    sample = samples[key]
    await callback.message.answer_photo(sample["photo_id"], sample["caption"])
    await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=sample["keyboard"])


# Другие обработчики
@get_info.message(F.text == "Бланк для заказа")
async def send_order_form(message: Message):
    await message.answer(blank_info)
    await message.answer_document(document=order_form, caption="Вот ваш бланк для заказа. Заполните его и отправьте нам!")


@get_info.message(F.text == "Где брать трек-номер")
async def send_track_number_info(message: Message):
    await message.answer('⬇️ <b>С какого сайта вы хотите получить информацию о получении трек-номеров?</b>',
                         reply_markup=where_get_keyboard)

@get_info.callback_query(F.data.startswith("where_get_with_"))
async def handle_simple(callback: CallbackQuery):
    photos = {
        "1688": [track_number_info_photo1_1688, track_number_info_photo2_1688],
        "Taobao": [track_number_info_photo1_Taobao, track_number_info_photo2_Taobao],
        "Pinduoduo": [track_number_info_photo1_Pinduoduo, track_number_info_photo2_Pinduoduo],
        "Poizon": [track_number_info_photo1_Poizon, track_number_info_photo2_Poizon]
    }

    key = callback.data.split("_")[-1]
    photo_key = photos.get(key)
    media = [InputMediaPhoto(media=photo_key[0], caption=key),
             InputMediaPhoto(media=photo_key[1])]
    await callback.message.answer_media_group(media)


@get_info.message(F.text == "Самовыкуп")
async def send_self_purchase(message: Message):
    user_id = await get_user_by_tg_id(message.from_user.id)
    await message.answer(self_purchase.format(f"{user_id[0]:04d}"))

@get_info.message(F.text == "Тарифы")
async def send_tariffs(message: Message):
    await message.answer(tariffs)

@get_info.message(F.text == "Страховка")
async def send_insurance(message: Message):
    await message.answer("<i>функция не разработана</i>")   # # # # # # # # # # #

@get_info.message(F.text == "Проверка товаров")
async def send_goods_check(message: Message):
    media = [InputMediaVideo(media=goods_check_video1),
        InputMediaPhoto(media=goods_check_photo1),
        InputMediaVideo(media=goods_check_video2),
        InputMediaPhoto(media=goods_check_photo2),
        InputMediaPhoto(media=goods_check_photo3)]
    await message.answer_media_group(media)
    await message.reply(goods_check)

@get_info.message(F.text == "Консолидация")
async def send_consolidation(message: Message):
    await message.answer_photo(consolidation_photo, consolidation)

@get_info.message(F.text == "Запрещённые товары")
async def send_forbidden_goods(message: Message):
    await message.answer(forbidden_goods)

# # # # # # # # # # #

@get_info.message(F.text == "Упаковка")
async def send_packing(message: Message):
    await message.answer(packing)


@get_info.message(F.text == "️Цены")  # Нету кнопки
async def price(message: Message):
    await message.answer_photo(
        "AgACAgIAAxkBAAPbZztu_WMs7OrFwLEW9wPUzWKoyJYAAvnqMRv6E-FJIrIRnk8frsgBAAMCAANzAAM2BA",
        "2,5$/КГ\n230/Куб")



# ОБРАБОТЧИК КОМАНДЫ "Мой профиль"
@get_info.message(F.text == "Мой профиль")
async def profile(message: Message):
    inf = await get_info_profile(message.from_user.id)
    if not inf: await message.answer("Профиль не найден.")
    no = "<i>Не заполнено</i>"
    await message.answer(
        f"Номер для заказов: <code>FS{inf.get('id'):04d}</code>\n"
        f"Имя: {inf.get('name') or no}\n"
        f"Номер: {inf.get('phone') or no}\n")
    await message.answer("Что нужно сделать ещё?", reply_markup=my_profile_keyboard)

@get_info.callback_query(F.data == "change_profile_data")
async def change_profile_data(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Что хотите изменить?", reply_markup=change_data_keyboard)

@get_info.callback_query(F.data == "my_track_codes")
async def my_track_codes(callback: CallbackQuery):
    await callback.message.delete()
    user_tg_id = callback.from_user.id
    track_codes = await get_user_track_codes(user_tg_id)

    if track_codes:
        response = "Ваши трек-коды:\n\n"
        for track_code, status in track_codes:
            response += f"<b>{track_code}</b> - <i>{'На складе' if status == 'in_stock' else 'Не на складе'}</i>\n"
        await callback.message.answer(response)
    else:
        await callback.message.answer("У вас нет зарегистрированных трек-кодов.\n"
                                      "Для того чтобы их добавить, просто поищите их через команду "
                                      "<code>Проверка трек-кода</code> и они автоматически сохраняться в ваши трек-коды")


@get_info.message(F.text == "Другие кнопки")
async def send_anther(message: Message):
    await message.answer("вот другие кнопки Фирузчон баратан", reply_markup=main_inline_keyboard)


# ОБРАБОТЧИК КОМАНДЫ НАЗАД В ГЛАВНОЕ МЕНЮ
@get_info.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)
