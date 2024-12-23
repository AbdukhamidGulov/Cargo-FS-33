from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup


def create_keyboard_button(text: str) -> KeyboardButton:
    return KeyboardButton(text=text)

def create_keyboard(buttons: list[list[KeyboardButton]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def create_inline_button(text: str, callback_data: str = None, url: str = None) -> InlineKeyboardButton:
    if url: return InlineKeyboardButton(text=text, url=url)
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Кнопки главного меню
warehouse_address_btn = create_keyboard_button("️Адрес склада")
check_track_number_btn = create_keyboard_button("Проверка трек-кода")
order_form_btn = create_keyboard_button("Бланк для заказа")
track_number_info_btn = create_keyboard_button("Где брать трек-номер")
self_purchase_btn = create_keyboard_button("Самовыкуп")
tariffs_btn = create_keyboard_button("Тарифы")
consolidation_btn = create_keyboard_button("Консолидация")
forbidden_goods_btn = create_keyboard_button("Запрещённые товары")
packing_btn = create_keyboard_button("Упаковка")
my_profile_btn = create_keyboard_button("Мой профиль")

main_keyboard = create_keyboard([
    [warehouse_address_btn, check_track_number_btn],
    [order_form_btn, track_number_info_btn],
    [self_purchase_btn, tariffs_btn],
    [consolidation_btn, forbidden_goods_btn],
    [packing_btn, my_profile_btn]
])

# Инлайн кнопки главного меню
calculate_volume_btn = create_inline_button(text="Рассчитать объём", callback_data="calculate_volume")
# calculate_shipping_btn = create_inline_button(text="Рассчитать доставку", callback_data="calc_shipping")
calculate_insurance_btn = create_inline_button(text="Рассчитать страховку", callback_data="calc_insurance")
goods_check_btn = create_inline_button(text="Проверка товаров", callback_data="goods_check")
request_for_verification_btn = create_inline_button(text="Заявка на проверку", callback_data="request_for_verification")
alipay_exchange_rate_btn = create_inline_button(text="Курс Alipay", url="https://t.me/Alipay_Chat_ru")
cargo_chat_btn = create_inline_button(text="Чат Карго FS-33", url="https://t.me/cargoFS33")
admin_panel_btn = create_inline_button(text="Админ", url="https://t.me/fir2201")

main_inline_keyboard = create_inline_keyboard([
    [calculate_volume_btn, calculate_insurance_btn],
    [goods_check_btn, request_for_verification_btn],
    [alipay_exchange_rate_btn, cargo_chat_btn],
    [admin_panel_btn]
])


# Админ кнопки
add_track_codes_btn = create_keyboard_button("️Добавить пребывшие на склад трек-коды")
add_sent_track_codes_btn = create_keyboard_button("Добавить отправленные трек-коды")
track_codes_list_btn = create_keyboard_button("️Список трек-кодов")
search_by_id_btn = create_keyboard_button("Искать информацию по ID")
back_to_main_menu_btn = create_keyboard_button("Вернуться в главное меню")

admin_keyboard = create_keyboard([
    [add_track_codes_btn], [add_sent_track_codes_btn], [track_codes_list_btn],
    [search_by_id_btn], [back_to_main_menu_btn]
])

# Кнопки регистрации
pass_reg_btn = create_inline_button("️Пропустить", "pass_reg")
do_reg_btn = create_inline_button("️Пройти регистрацию", "do_reg")
reg_keyboard = create_inline_keyboard([[pass_reg_btn, do_reg_btn]])

# Кнопки профиля
my_track_codes_btn = create_inline_button("️Мои трек коды", "my_track_codes")
change_data_btn = create_inline_button("️Изменит данные", "change_profile_data")
my_profile_keyboard = create_inline_keyboard([[change_data_btn, my_track_codes_btn]])

# Кнопки изменений данных профиля
change_name_btn = create_inline_button("Имя и фамилию", "change_name")
change_phone_btn = create_inline_button("Телефон", "change_phone")
change_data_keyboard = create_inline_keyboard([[change_name_btn], [change_phone_btn]])

# Кнопки образцов
simple_1688_btn = create_inline_button("️Образец 1688", "simple_1688")
simple_Taobao_btn = create_inline_button("️Образец Taobao", "simple_Taobao")
simple_Pinduoduo_btn = create_inline_button("️Образец Pinduoduo", "simple_Pinduoduo")
simple_Poizon_btn = create_inline_button("️Образец Poizon", "simple_Poizon")
samples_keyboard = create_inline_keyboard([
    [simple_1688_btn, simple_Taobao_btn],
    [simple_Pinduoduo_btn, simple_Poizon_btn]
])
samples_1688_keyboard = create_inline_keyboard([[simple_Taobao_btn], [simple_Pinduoduo_btn], [simple_Poizon_btn]])
samples_Taobao_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Pinduoduo_btn], [simple_Poizon_btn]])
samples_Pinduoduo_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Taobao_btn], [simple_Poizon_btn]])
samples_Poizon_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Taobao_btn], [simple_Pinduoduo_btn]])

# Кнопки, где брать трек номера
where_get_1688_btn = create_inline_button("С 1688", "where_get_with_1688")
where_get_Taobao_btn = create_inline_button("С Taobao", "where_get_with_Taobao")
where_get_Pinduoduo_btn = create_inline_button("С Pinduoduo", "where_get_with_Pinduoduo")
where_get_Poizon_btn = create_inline_button("️С Poizon", "where_get_with_Poizon")

where_get_keyboard = create_inline_keyboard([
    [where_get_1688_btn, where_get_Taobao_btn],
    [where_get_Pinduoduo_btn, where_get_Poizon_btn]
])

# Кнопка отмена в добавление трек-номеров
cancel_keyboard = create_keyboard([[create_keyboard_button("Отмена")]])

# Кнопки выбора типа товаров
bulk_cargo_btn = create_keyboard_button("Объёмный груз")
electronics_btn = create_keyboard_button("Электроника")
laptops_btn = create_keyboard_button("Ноутбуки")
phones_btn = create_keyboard_button("Телефоны")
pharmacy_btn = create_keyboard_button("Аптека")
clothing_btn = create_keyboard_button("Одежда")
fabric_btn = create_keyboard_button("Ткань")
food_btn = create_keyboard_button("Продукты")

item_type_keyboard = create_keyboard([
    [bulk_cargo_btn, electronics_btn],
    [laptops_btn, phones_btn, pharmacy_btn],
    [clothing_btn, fabric_btn, food_btn]
])
