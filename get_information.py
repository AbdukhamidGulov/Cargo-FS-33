from aiogram.types import CallbackQuery, Message
from aiogram import F, Router

from database import get_info_profile, get_user_by_tg_id, get_user_track_codes
from keyboards import (my_profile_keyboard, samples_keyboard, samples_1688_keyboard, samples_Taobao_keyboard,\
                       samples_Pinduoduo_keyboard, samples_Poizon_keyboard, main_keyboard, change_data_keyboard)

get_info = Router()


# ВСЯ ОБРАБОТКА ДЛЯ АДРЕСА СКЛАДА И ОБРАЗЦОВ
@get_info.message(F.text == "️Адрес склада")
async def address(message: Message):
    user_id = await get_user_by_tg_id(message.from_user.id)
    await message.answer(f"<u>Адрес склада</u>\n收件人：<code>FS{user_id[0]:04d}</code>\n"
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


# Обрабтчик для отправения БЛАНКА
@get_info.message(F.text == "Бланк для заказа")
async def send_order_form(message: Message):
    await message.answer_document(document="BQACAgIAAxkBAAIFOGdMdX50fhlJbYDkoijeDvetdoJiAAJLPgACq454SXUIYnLcX1a5NgQ",
                                  caption="Вот ваш бланк для заказа. Заполните его и отправьте нам!")


# Обрабтчик для отправения ИНФОРМАЦИИ о том Где брать трек-номер
@get_info.message(F.text == "Где брать трек-номер")
async def send_order_form(message: Message):
    await message.answer("⬇️ <b>Где брать трек номер.</b>")
    await message.answer_photo("AgACAgIAAxkBAAIFRGdMfYbh30o5AeHeq3M421ylzr5cAAIb4jEbd4JoSz82D2nJhJjpAQADAgADcwADNgQ")
    await message.answer_photo(
        "AgACAgIAAxkBAAIFRmdMfbGjsYmbP6dvqpw1pagB8OWqAAIa4jEbd4JoS2OOutkxjRHwAQADAgADcwADNgQ"," 💴 1688" )
    await message.answer("Taobao.\nPoizon.\nPinduoduo.")


@get_info.message(F.text == "Самовыкуп")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33/78">Нажмите чтобы узнать о Самовыкупе</a>')


@get_info.message(F.text == "Тарифы")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33/84">Нажмите чтобы узнать о Тарифах</a>')


@get_info.message(F.text == "Страховка")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33/97">Нажмите чтобы узнать о Страховке</a>')


@get_info.message(F.text == "Проверка товаров")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33/2241">Нажмите чтобы узнать о Проверке товаров</a>')


@get_info.message(F.text == "Консолидация")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33/107">Нажмите чтобы узнать о Консолидации</a>')


@get_info.message(F.text == "Запрещённые товары")
async def x_tovar(message: Message):
    pd = ("<b>НАШЕ КАРГО НЕ ПРИНИМАЕТ СЛЕДУЮЩИЕ ВИДЫ ПОСЫЛОК!</b>\n\n"
          "1. <b>Лекарства</b> (порошки, таблетки, лекарства в виде жидкостей).\n\n"
          "2. <b>Все виды холодного оружия</b> (ножи, электрошокеры, биты и другое данного характера) "
          "полностью запрещены.\n\n"
          "3. <b>Всё что запрещено на РФ</b> (Военные товары, химия, растения, семена, газ, электронные сигареты)")
    await message.answer(pd)


@get_info.message(F.text == "Курс Alipay")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/Alipay_Chat_ru">Нажмите чтобы узнать о "Курсе Alipay"</a>')


@get_info.message(F.text == "Чат Карго FS-33")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33">Нажмите чтобы войти в Чат Карго FS-33"</a>')


@get_info.message(F.text == "Админ")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/fir2201">Нажмите чтобы связатся с админом</a>')


@get_info.message(F.text == "Упаковка")
async def send_order_form(message: Message):
    await message.answer('<a href="https://t.me/cargoFS33/70">Нажмите чтобы узнать об Упаковке</a>')


@get_info.message(F.text == "️Цены")  # Нету кнопки
async def price(message: Message):
    await message.answer_photo(
        "AgACAgIAAxkBAAPbZztu_WMs7OrFwLEW9wPUzWKoyJYAAvnqMRv6E-FJIrIRnk8frsgBAAMCAANzAAM2BA",
        "2,5$/КГ\n230/Куб")



# ОБРАБОТЧИК КОМАНДЫ "Мой профиль"
@get_info.message(F.text == "️Мой профиль")
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
    user_tg_id = callback.from_user.id
    track_codes = await get_user_track_codes(user_tg_id)

    if track_codes:
        response = "Ваши трек-коды:\n\n"
        for track_code, status in track_codes:
            response += f"<b>{track_code}</b> - <i>{'На складе' if status == 'in_stock' else 'Не на скаде'}</i>\n"
        await callback.message.answer(response)
    else:
        await callback.message.answer("У вас нет зарегистрированных трек-кодов.\n"
                                      "Для их регистрации поищите их через команду <code>Проверка трек-кода</code>")


# ОБРАБОТЧИК КОМАНДЫ НАЗАД В ГЛАВНОЕ МЕНЮ
@get_info.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)
