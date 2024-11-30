from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup


def create_keyboard_button(text: str) -> KeyboardButton:
    return KeyboardButton(text=text)

def create_button(text: str, callback_data: str = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=buttons)

checking_track_code_btn = create_keyboard_button("Проверка трек-кода")
price_btn = create_keyboard_button("️Цены")
warehouse_address_btn = create_keyboard_button("️Адрес склада")
prohibited_goods_btn = create_keyboard_button("️Запрещённые товары")
calculator_btn = create_keyboard_button("Рассчитать стоимость")
my_profile_btn = create_keyboard_button("️Мой профиль")

pass_reg_btn = create_button("️Пропустить", "pass_reg")
do_reg_btn = create_button("️Пройти регистрацию", "do_reg")

my_track_codes_btn = create_button("️Мои трек коды", "my_track_codes")
change_data_btn = create_button("️Изменит данные", "change_profile_data")

change_name_btn = create_button("Имя и фамилию", "change_name")
change_phone_btn = create_button("Телефон", "change_phone")
change_address_btn = create_button("️Адрес", "change_address")

simple_1688_btn = create_button("️Образец 1688", "simple_1688")
simple_Taobao_btn = create_button("️Образец Taobao", "simple_Taobao")
simple_Pinduoduo_btn = create_button("️Образец Pinduoduo", "simple_Pinduoduo")
simple_Poizon_btn = create_button("️Образец Poizon", "simple_Poizon")

add_track_codes_btn = create_button("️Добавить трек-коды", "add_track_codes")
track_codes_list_btn = create_button("️Список трек-кодов", "track_codes_list")
recreate_db_btn = create_button("️Пересоздать БД пользователей", "recreate_db")
recreate_tc_btn = create_button("️Пересоздать БД трек-номеров", "recreate_tc")

main_keyboard = ReplyKeyboardMarkup(keyboard=[
    [checking_track_code_btn, price_btn],
    [calculator_btn, warehouse_address_btn],
    [prohibited_goods_btn, my_profile_btn]], resize_keyboard=True)

reg_keyboard = create_inline_keyboard([[pass_reg_btn, do_reg_btn]])

my_profile_keyboard = create_inline_keyboard([[change_data_btn, my_track_codes_btn]])

change_data_keyboard = create_inline_keyboard([[change_name_btn],
                                               [change_phone_btn],
                                               [change_address_btn]])

samples_keyboard = create_inline_keyboard([[simple_1688_btn, simple_Taobao_btn],
                                           [simple_Pinduoduo_btn, simple_Poizon_btn]])
samples_1688_keyboard = create_inline_keyboard([[simple_Taobao_btn], [simple_Pinduoduo_btn], [simple_Poizon_btn]])
samples_Taobao_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Pinduoduo_btn], [simple_Poizon_btn]])
samples_Pinduoduo_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Taobao_btn], [simple_Poizon_btn]])
samples_Poizon_keyboard = create_inline_keyboard([[simple_1688_btn], [simple_Taobao_btn], [simple_Pinduoduo_btn]])

admin_keyboard = create_inline_keyboard([[add_track_codes_btn], [track_codes_list_btn],
                                         [recreate_db_btn], [recreate_tc_btn]])
