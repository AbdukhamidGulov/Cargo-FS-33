from aiogram.types import CallbackQuery
from aiogram import F, Router, Bot

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
async def add_raper(callback: CallbackQuery):
    await callback.message.answer("Мой профиль👤")