from aiogram.types import CallbackQuery
from aiogram import F, Router, Bot

from database import get_info_profile
from keyboards import my_profile_keyboard, back_to_menu_keyboard

gi = Router()

@gi.callback_query(F.data == "checking_track_code")
async def add_raper(callback: CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id, "Проверка трек кода🔎")

@gi.callback_query(F.data == "price")
async def add_raper(callback: CallbackQuery, bot: Bot):
    await callback.message.answer_photo("AgACAgIAAxkBAAPbZztu_WMs7OrFwLEW9wPUzWKoyJYAAvnqMRv6E-FJIrIRnk8frsgBAAMCAANzAAM2BA", "2,5$/КГ\n230/Куб")

@gi.callback_query(F.data == "warehouse_address")
async def add_raper(callback: CallbackQuery):
    await callback.message.answer("Адрес складов🗺")

@gi.callback_query(F.data == "prohibited_goods")
async def add_raper(callback: CallbackQuery):
    pd = ("    <b>НАШЕ КАРГО НЕ ПРИНИМАЕТ СЛЕДУЮЩИЕ ВИДЫ ПОСЫЛОК!</b>\n\n"
          "1. <b>Лекарства</b> (порошки, таблетки, лекарства в виде жидкостей).\n\n"
          "2. <b>Все виды холодного оружия</b> (ножи, электрошокеры, биты и другое данного характера) "
          "полностью запрещены.\n\n3. <b>Техника</b> (Мобильные телефоны, планшеты, ноутбуки и т.д)")
    await callback.message.answer(pd)

@gi.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery):
    inf = await get_info_profile(callback.from_user.id)
    print(inf)
    if not inf: await callback.message.answer("Профиль не найден.", reply_markup=back_to_menu_keyboard)
    no = "<i>Не заполнено</i>"
    await callback.message.answer(
        f"Номер для заказов: <code>FS{inf.get('id', '0000'):04d}</code>\n"
        f"Имя: {inf.get('name', no)}\n"
        f"Номер: {inf.get('number', no)}\n"
        f"Адрес: {inf.get('city', no)}\n"
        f"Трек коды: {inf.get('track_codes', "Нет трек кодов")}\n", reply_markup=my_profile_keyboard)
