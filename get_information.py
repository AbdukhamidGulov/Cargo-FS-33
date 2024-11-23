from aiogram.types import CallbackQuery, Message
from aiogram import F, Router, Bot

from database import get_info_profile, get_user_by_tg_id, update_user_info
from keyboards import my_profile_keyboard, back_to_menu_keyboard, samples_keyboard, samples_1688_keyboard, \
    samples_Taobao_keyboard, samples_Pinduoduo_keyboard, samples_Poizon_keyboard, main_keyboard, data_updated_keyboard

gi = Router()


@gi.callback_query(F.data == "checking_track_code")
async def checking_track_code(callback: CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id, "Проверка трек кода🔎")


@gi.callback_query(F.data == "price")
async def price(callback: CallbackQuery, bot: Bot):
    await callback.message.answer_photo(
        "AgACAgIAAxkBAAPbZztu_WMs7OrFwLEW9wPUzWKoyJYAAvnqMRv6E-FJIrIRnk8frsgBAAMCAANzAAM2BA", "2,5$/КГ\n230/Куб")


# ВСЯ ОБРАБОТКА ДЛЯ АДРЕСА СКЛАДА И ОБРАЗЦОВ
@gi.callback_query(F.data == "warehouse_address")
async def warehouse_address(callback: CallbackQuery):
    user_id = await get_user_by_tg_id(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(f"   <u>Адрес склада</u>\n收件人：<code>FS{user_id[0]:04d}</code>\n"
                                  f"电话号码：<code>15116957545</code>\n"
                                  f"地址：<code>佛山市南海区大沥镇黄岐泌冲凤秀岗工业区凤秀大楼18号3档  FS{user_id[0]:04d} "
                                  f"发货一定要写名字，麦头，不然仓库不收</code>")
    await callback.message.answer("Нажмите чтобы увидеть образцы", reply_markup=samples_keyboard)


@gi.callback_query(F.data == "simple_1688")
async def simple_1688(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        "AgACAgIAAxkBAAIBimc_ZKt4RFZIx-jpBI116ulY13LAAAKq7DEbu-rwSQ6olox6fGduAQADAgADcwADNgQ", "Образец 1688")
    await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=samples_1688_keyboard)

@gi.callback_query(F.data == "simple_Taobao")
async def simple_taobao(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        "AgACAgIAAxkBAAIBjGc_ZR4880Smla-5Bgd2Sjnn_AbyAAKt7DEbu-rwSXoONn0x9TuXAQADAgADcwADNgQ", "Образец Taobao")
    await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=samples_Taobao_keyboard)

@gi.callback_query(F.data == "simple_Pinduoduo")
async def simple_pinduoduo(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        "AgACAgIAAxkBAAIBjmc_ZYPMxuT9j_Zb5UgVlsb_l3H0AAKu7DEbu-rwSdaIN5anq7SqAQADAgADcwADNgQ", "Образец Pinduoduo")
    await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=samples_Pinduoduo_keyboard)

@gi.callback_query(F.data == "simple_Poizon")
async def simple_poizon(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        "AgACAgIAAxkBAAIBkGc_ZdXomhwB_-CBUdPwO5bsAswkAAJD5zEbrMfxSV5EjAkSWiH9AQADAgADcwADNgQ", "Образец poizon")
    await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=samples_Poizon_keyboard)


# ОБРАБОТЧИК - ЗАРЕЩЁННЫЕ ВЕЩЕСТВА
@gi.callback_query(F.data == "prohibited_goods")
async def prohibited_goods(callback: CallbackQuery):
    pd = ("    <b>НАШЕ КАРГО НЕ ПРИНИМАЕТ СЛЕДУЮЩИЕ ВИДЫ ПОСЫЛОК!</b>\n\n"
          "1. <b>Лекарства</b> (порошки, таблетки, лекарства в виде жидкостей).\n\n"
          "2. <b>Все виды холодного оружия</b> (ножи, электрошокеры, биты и другое данного характера) "
          "полностью запрещены.\n\n3. <b>Техника</b> (Мобильные телефоны, планшеты, ноутбуки и т.д)")
    await callback.message.answer(pd)


# ОБРАБОТЧИК КОМАНДЫ "my_profile"
@gi.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery):
    inf = await get_info_profile(callback.from_user.id)
    if not inf: await callback.message.answer("Профиль не найден.", reply_markup=back_to_menu_keyboard)
    no = "<i>Не заполнено</i>"
    await callback.message.delete()
    await callback.message.answer(
        f"Номер для заказов: <code>FS{inf.get('id'):04d}</code>\n"
        f"Имя: {inf.get('name') or no}\n"
        f"Номер: {inf.get('phone') or no}\n"
        f"Адрес доставки: {inf.get('address') or no}\n"
        f"Трек коды: {inf.get('track_codes') or '<i>Нет трек кодов</i>'}\n")
    await callback.message.answer("Нажмите чтобы изменит данные...", reply_markup=my_profile_keyboard)

# ОБРАБОТЧИК ИЗМЕНЕНЫЙ
@gi.callback_query(F.data.startswith("change_"))
async def change_info(callback: CallbackQuery):
    await callback.message.delete()
    field = callback.data.split("_")[-1]  # name, number, address
    d = {"name": "новое имя", "number": "новый номер телефона", "address": "новый адрес"}
    await callback.message.answer(f"Введите {d[field]}:")

    @gi.message()
    async def process_new_name(message: Message):
        new_name = message.text
        await update_user_info(message.from_user.id, field, new_name)
        await message.answer("Успешно обновлено.", reply_markup=data_updated_keyboard)


# ОБРАБОТЧИК КОМАНДЫ НАЗАД В ГЛАВНОЕ МЕНЮ
@gi.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)