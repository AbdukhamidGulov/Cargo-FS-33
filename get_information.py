from aiogram.types import CallbackQuery, Message
from aiogram import F, Router

from database import get_info_profile, get_user_by_tg_id
from keyboards import (my_profile_keyboard, samples_keyboard, samples_1688_keyboard, samples_Taobao_keyboard,\
                       samples_Pinduoduo_keyboard, samples_Poizon_keyboard, main_keyboard, change_data_keyboard)

get_info = Router()


@get_info.message(F.text == "️Цены 💲")
async def price(message: Message):
    await message.answer_photo(
        "AgACAgIAAxkBAAPbZztu_WMs7OrFwLEW9wPUzWKoyJYAAvnqMRv6E-FJIrIRnk8frsgBAAMCAANzAAM2BA", "2,5$/КГ\n230/Куб")


# ВСЯ ОБРАБОТКА ДЛЯ АДРЕСА СКЛАДА И ОБРАЗЦОВ
@get_info.message(F.text == "️Адрес склада🗺")
async def address(message: Message):
    user_id = await get_user_by_tg_id(message.from_user.id)
    await message.answer(f"   <u>Адрес склада</u>\n收件人：<code>FS{user_id[0]:04d}</code>\n"
                                  f"电话号码：<code>15116957545</code>\n"
                                  f"地址：<code>佛山市南海区大沥镇黄岐泌冲凤秀岗工业区凤秀大楼18号3档  FS{user_id[0]:04d} "
                                  f"发货一定要写名字，麦头，不然仓库不收</code>")
    await message.answer("Нажмите чтобы увидеть образцы", reply_markup=samples_keyboard)


@get_info.callback_query(F.data.startswith("simple_"))
async def handle_simple(callback: CallbackQuery):
    await callback.message.delete()
    samples = {
        "1688": {
            "photo_id": "AgACAgIAAxkBAAIBimc_ZKt4RFZIx-jpBI116ulY13LAAAKq7DEbu-rwSQ6olox6fGduAQADAgADcwADNgQ",
            "caption": "Образец 1688", "keyboard": samples_1688_keyboard},
        "Taobao": {
            "photo_id": "AgACAgIAAxkBAAIBjGc_ZR4880Smla-5Bgd2Sjnn_AbyAAKt7DEbu-rwSXoONn0x9TuXAQADAgADcwADNgQ",
            "caption": "Образец Taobao", "keyboard": samples_Taobao_keyboard},
        "Pinduoduo": {
            "photo_id": "AgACAgIAAxkBAAIBjmc_ZYPMxuT9j_Zb5UgVlsb_l3H0AAKu7DEbu-rwSdaIN5anq7SqAQADAgADcwADNgQ",
            "caption": "Образец Pinduoduo", "keyboard": samples_Pinduoduo_keyboard},
        "Poizon": {
            "photo_id": "AgACAgIAAxkBAAIBkGc_ZdXomhwB_-CBUdPwO5bsAswkAAJD5zEbrMfxSV5EjAkSWiH9AQADAgADcwADNgQ",
            "caption": "Образец poizon", "keyboard": samples_Poizon_keyboard}}

    key = callback.data.split("_")[-1]
    sample = samples[key]
    await callback.message.answer_photo(sample["photo_id"], sample["caption"])
    await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=sample["keyboard"])


# ОБРАБОТЧИК - ЗАРЕЩЁННЫЕ ВЕЩЕСТВА
@get_info.message(F.text == "️Запрещённые товары ❌")
async def x_tovar(message: Message):
    pd = ("    <b>НАШЕ КАРГО НЕ ПРИНИМАЕТ СЛЕДУЮЩИЕ ВИДЫ ПОСЫЛОК!</b>\n\n"
          "1. <b>Лекарства</b> (порошки, таблетки, лекарства в виде жидкостей).\n\n"
          "2. <b>Все виды холодного оружия</b> (ножи, электрошокеры, биты и другое данного характера) "
          "полностью запрещены.\n\n3. <b>Техника</b> (Мобильные телефоны, планшеты, ноутбуки и т.д)")
    await message.answer(pd)


# ОБРАБОТЧИК КОМАНДЫ "my_profile"
@get_info.message(F.text == "️Мой профиль👤")
async def profile(message: Message):
    inf = await get_info_profile(message.from_user.id)
    if not inf: await message.answer("Профиль не найден.")
    no = "<i>Не заполнено</i>"
    await message.answer(
        f"Номер для заказов: <code>FS{inf.get('id'):04d}</code>\n"
        f"Имя: {inf.get('name') or no}\n"
        f"Номер: {inf.get('phone') or no}\n"
        f"Адрес доставки: {inf.get('address') or no}\n")
    await message.answer("Что нужно сделать ещё?", reply_markup=my_profile_keyboard)

@get_info.callback_query(F.data == "change_profile_data")
async def change_profile_data(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Что хотите изменить?", reply_markup=change_data_keyboard)

@get_info.callback_query(F.data == "my_track_codes")
async def my_track_codes(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("")


# ОБРАБОТЧИК КОМАНДЫ НАЗАД В ГЛАВНОЕ МЕНЮ
@get_info.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)

