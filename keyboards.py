from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup


def create_keyboard_button(text: str) -> KeyboardButton:
    return KeyboardButton(text=text)

def create_keyboard(buttons: list[list[KeyboardButton]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def create_inline_button(text: str, callback_data: str = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Кнопки гавного меню
warehouse_address_btn = create_keyboard_button("️Адрес склада")
order_form_btn = create_keyboard_button("Бланк для заказа")
track_number_info_btn = create_keyboard_button("Где брать трек-номер")
self_purchase_btn = create_keyboard_button("Самовыкуп")
tariffs_btn = create_keyboard_button("Тарифы")
insurance_btn = create_keyboard_button("Страховка")
goods_check_btn = create_keyboard_button("Проверка товаров")
consolidation_btn = create_keyboard_button("Консолидация")
check_track_number_btn = create_keyboard_button("Проверка трек-кода")
delivery_cost_calc_btn = create_keyboard_button("Рассчитать стоимость доставки")  # Проверка нокарда
forbidden_goods_btn = create_keyboard_button("Запрещённые товары")
alipay_exchange_rate_btn = create_keyboard_button("Курс Alipay")
cargo_chat_btn = create_keyboard_button("Чат Карго FS-33")
admin_panel_btn = create_keyboard_button("Админ")
packing_btn = create_keyboard_button("Упаковка")
my_profile_btn = create_keyboard_button("Мой профиль")

# Админ кнопки
add_track_codes_btn = create_keyboard_button("️Добавить трек-коды")
track_codes_list_btn = create_keyboard_button("️Список трек-кодов")
recreate_db_btn = create_keyboard_button("️Пересоздать БД пользователей")
recreate_tc_btn = create_keyboard_button("️Пересоздать БД трек-номеров")
back_to_main_menu_btn = create_keyboard_button("Вернутся в главное меню")

pass_reg_btn = create_inline_button("️Пропустить", "pass_reg")
do_reg_btn = create_inline_button("️Пройти регистрацию", "do_reg")

my_track_codes_btn = create_inline_button("️Мои трек коды", "my_track_codes")
change_data_btn = create_inline_button("️Изменит данные", "change_profile_data")

change_name_btn = create_inline_button("Имя и фамилию", "change_name")
change_phone_btn = create_inline_button("Телефон", "change_phone")
change_address_btn = create_inline_button("️Адрес", "change_address")

simple_1688_btn = create_inline_button("️Образец 1688", "simple_1688")
simple_Taobao_btn = create_inline_button("️Образец Taobao", "simple_Taobao")
simple_Pinduoduo_btn = create_inline_button("️Образец Pinduoduo", "simple_Pinduoduo")
simple_Poizon_btn = create_inline_button("️Образец Poizon", "simple_Poizon")


main_keyboard = create_keyboard([
    [warehouse_address_btn, order_form_btn],
    [track_number_info_btn, self_purchase_btn],
    [tariffs_btn, insurance_btn],
    [goods_check_btn, consolidation_btn],
    [check_track_number_btn, delivery_cost_calc_btn],
    [forbidden_goods_btn, alipay_exchange_rate_btn],
    [cargo_chat_btn, admin_panel_btn],
    [packing_btn, my_profile_btn]
])

admin_keyboard = create_keyboard([
    [add_track_codes_btn], [track_codes_list_btn],
    [recreate_db_btn], [recreate_tc_btn],
    [back_to_main_menu_btn]
])


reg_keyboard = create_inline_keyboard([[pass_reg_btn, do_reg_btn]])

my_profile_keyboard = create_inline_keyboard([[change_data_btn, my_track_codes_btn]])

change_data_keyboard = create_inline_keyboard([
    [change_name_btn],
    [change_phone_btn],
    [change_address_btn]
])

samples_keyboard = create_inline_keyboard([
    [simple_1688_btn, simple_Taobao_btn],
    [simple_Pinduoduo_btn, simple_Poizon_btn]
])
samples_1688_keyboard = create_inline_keyboard([[simple_Taobao_btn], [simple_Pinduoduo_btn], [simple_Poizon_btn]])
samples_Taobao_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Pinduoduo_btn], [simple_Poizon_btn]])
samples_Pinduoduo_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Taobao_btn], [simple_Poizon_btn]])
samples_Poizon_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Taobao_btn], [simple_Pinduoduo_btn]])
