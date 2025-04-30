from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram import F, Router

from database.info_content import get_info_content
from database.users import get_info_profile, get_user_by_tg_id
from keyboards import main_keyboard, where_get_keyboard, reg_keyboard, create_samples_keyboard

get_info_router = Router()


# ВСЯ ОБРАБОТКА ДЛЯ АДРЕСА СКЛАДА И ОБРАЗЦОВ
@get_info_router.callback_query(F.data == "warehouse_address")
async def address(callback: CallbackQuery):
    """Отправляет адрес склада пользователю."""
    id_from_user = await get_user_by_tg_id(callback.from_user.id)
    if not id_from_user:
        await callback.answer(
            "❌ Вы не зарегистрированы!\n\nХотите зарегистрироваться?", reply_markup=reg_keyboard)
        return
    fs = f"{id_from_user:04d}"
    warehouse_address_template = await get_info_content("warehouse_address")
    if warehouse_address_template:
        await callback.message.answer(warehouse_address_template.format(fs))
        await callback.message.answer("Нажмите чтобы увидеть образцы", reply_markup=create_samples_keyboard())
    else:
        await callback.message.answer("Адрес склада не найден. Обратитесь к администратору.")


@get_info_router.callback_query(F.data.startswith("simple_"))
async def handle_simple(callback: CallbackQuery):
    """Обрабатывает запрос на отображение образца."""
    await callback.message.delete()
    key = callback.data.split("_")[-1]
    photo_id = await get_info_content(f"sample_{key}")
    if photo_id:
        caption = f"Образец {key}"
        samples_keyboard = create_samples_keyboard(key)
        await callback.message.answer_photo(photo_id, caption)
        await callback.message.answer("Нажмите чтобы увидеть другие образцы", reply_markup=samples_keyboard)
    else:
        await callback.message.answer("Образец не найден.")


# Другие обработчики
@get_info_router.message(F.text == "Бланк для заказа")
async def send_order_form(message: Message):
    """Отправляет бланк для заказа."""
    blank_info_text = await get_info_content("blank_text")
    order_form_doc = await get_info_content("order_form")
    if blank_info_text and order_form_doc:
        await message.answer(blank_info_text)
        await message.answer_document(document=order_form_doc, caption="Вот ваш бланк для заказа. Заполните его и отправьте нам!")
    else:
        await message.answer("Информация о бланке не найдена.")


@get_info_router.message(F.text == "Где брать трек-номер")
async def send_track_number_info(message: Message):
    """Запрашивает у пользователя выбор сайта для получения информации о трек-номерах."""
    await message.answer('⬇️ <b>С какого сайта вы хотите получить информацию о получении трек-номеров?</b>',
                         reply_markup=where_get_keyboard)


@get_info_router.callback_query(F.data.startswith("where_get_with_"))
async def handle_track_info(callback: CallbackQuery):
    """Отправляет фото с информацией о трек-номерах для выбранного сайта."""
    key = callback.data.split("_")[-1]
    photo1 = await get_info_content(f"track_code_{key}_photo1")
    photo2 = await get_info_content(f"track_code_{key}_photo2")
    if photo1 and photo2:
        media = [InputMediaPhoto(media=photo1, caption=key),
                 InputMediaPhoto(media=photo2)]
        await callback.message.answer_media_group(media)
    else:
        await callback.message.answer("Информация о трек-номерах не найдена.")


@get_info_router.message(F.text == "Тарифы")
async def send_tariffs(message: Message):
    """Отправляет информацию о тарифах."""
    tariffs_text = await get_info_content("tariffs_text")
    tariffs_document = await get_info_content("tariffs_document")
    if tariffs_text:
        await message.answer(tariffs_text)
    if tariffs_document:
        await message.answer_document(document=tariffs_document)
    else:
        await message.answer("Информация о тарифах не найдена.")


@get_info_router.message(F.text == "Проверка товаров")
async def send_goods_check(message: Message):
    """Отправляет медиа и текст о проверке товаров."""
    video1 = await get_info_content("goods_check_video1")
    photo1 = await get_info_content("goods_check_photo1")
    video2 = await get_info_content("goods_check_video2")
    photo2 = await get_info_content("goods_check_photo2")
    photo3 = await get_info_content("goods_check_photo3")
    goods_check_text = await get_info_content("goods_check_text")
    if all([video1, photo1, video2, photo2, photo3, goods_check_text]):
        media = [InputMediaVideo(media=video1),
                 InputMediaPhoto(media=photo1),
                 InputMediaVideo(media=video2),
                 InputMediaPhoto(media=photo2),
                 InputMediaPhoto(media=photo3)]
        await message.answer_media_group(media)
        await message.reply(goods_check_text, reply_markup=main_keyboard)
    else:
        await message.answer("Информация о проверке товаров не найдена.")


@get_info_router.message(F.text == "Консолидация")
async def send_consolidation(message: Message):
    """Отправляет фото и текст о консолидации."""
    inf = await get_info_profile(message.from_user.id)
    if not inf:
        await message.answer("Профиль не найден.")
        return
    consolidation_photo_id = await get_info_content("consolidation_photo")
    consolidation_text = await get_info_content("consolidation_text")
    if consolidation_photo_id and consolidation_text:
        await message.answer_photo(consolidation_photo_id, consolidation_text.format(f"<code>FS{inf.get('id'):04d}</code>"),
                                   show_caption_above_media=True)
    else:
        await message.answer("Информация о консолидации не найдена.")


@get_info_router.message(F.text == "Запрещённые товары")
async def send_forbidden_goods(message: Message):
    """Отправляет информацию о запрещённых товарах."""
    forbidden_goods_text = await get_info_content("forbidden_goods")
    if forbidden_goods_text:
        await message.answer(forbidden_goods_text)
    else:
        await message.answer("Информация о запрещённых товарах не найдена.")


@get_info_router.message(F.text == "Упаковка")
async def send_packing(message: Message):
    """Отправляет фото и текст об упаковке."""
    packing_photo_id = await get_info_content("packing_photo")
    packing_text = await get_info_content("packing_text")
    if packing_photo_id and packing_text:
        await message.answer_photo(packing_photo_id, packing_text)
    else:
        await message.answer("Информация об упаковке не найдена.")


@get_info_router.message(F.text == "️Цены")
async def send_prices(message: Message):
    """Отправляет информацию о ценах."""
    prices_document = await get_info_content("prices_document")
    prices_text = await get_info_content("prices_text")
    if prices_document and prices_text:
        await message.answer_document(document=prices_document, caption=prices_text)
        await message.answer_photo(prices_document, prices_text)
    else:
        await message.answer("Информация о ценах не найдена.")


# ОБРАБОТЧИК КОМАНДЫ НАЗАД В ГЛАВНОЕ МЕНЮ
@get_info_router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возвращает пользователя в главное меню."""
    await callback.message.delete()
    await callback.message.answer("Как я могу вам помочь?", reply_markup=main_keyboard)
