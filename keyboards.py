from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_button(text: str, callback_data: str = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=buttons)

checking_track_code_btn = create_button("️Проверка трек кода🔎", "checking_track_code")
price_btn = create_button("️Цены 💲", "price")
warehouse_address_btn = create_button("️Адрес склада🗺", "warehouse_address")
prohibited_goods_btn = create_button("️Запрещённые товары ❌", "prohibited_goods")
calculator_btn = create_button("Рассчитать стоимость 💸", "calculator")
my_profile_btn = create_button("️Мой профиль👤", "my_profile")

pass_reg_btn = create_button("️Пропустить", "pass_reg")
do_reg_btn = create_button("️Пройти регистрацию", "do_reg")

change_name_btn = create_button("Изменит имя и фамилию", "change_name")
change_phone_btn = create_button("️Изменить телефон", "change_phone")
change_address_btn = create_button("️Изменит адрес", "change_address")
my_track_code_btn = create_button("️Мои трек коды", "my_track_code")
main_menu_btn = create_button("️Назад в главное меню", "main_menu")

simple_1688_btn = create_button("️Образец 1688", "simple_1688")
simple_Taobao_btn = create_button("️Образец Taobao", "simple_Taobao")
simple_Pinduoduo_btn = create_button("️Образец Pinduoduo", "simple_Pinduoduo")
simple_Poizon_btn = create_button("️Образец Poizon", "simple_Poizon")

add_track_codes_btn = create_button("️", "add_track_codes")
track_codes_list_btn = create_button("️", "track_codes_list")
recreate_db_btn = create_button("️", "recreate_db")
recreate_tc_btn = create_button("️", "recreate_tc")

main_keyboard = create_inline_keyboard([[checking_track_code_btn],
                                        [price_btn, warehouse_address_btn],
                                        [prohibited_goods_btn, calculator_btn],
                                        [my_profile_btn]])

reg_keyboard = create_inline_keyboard([[pass_reg_btn, do_reg_btn]])

my_profile_keyboard = create_inline_keyboard([[change_name_btn, change_phone_btn],
                                              [change_address_btn, my_track_code_btn],
                                              [main_menu_btn]])

back_to_menu_keyboard = create_inline_keyboard([[main_menu_btn]])

samples_keyboard = create_inline_keyboard([[simple_1688_btn, simple_Taobao_btn],
                                           [simple_Pinduoduo_btn, simple_Poizon_btn],
                                           [main_menu_btn]])
samples_1688_keyboard = create_inline_keyboard([[simple_Taobao_btn, simple_Pinduoduo_btn], [simple_Poizon_btn, main_menu_btn]])
samples_Taobao_keyboard = create_inline_keyboard([[simple_1688_btn, simple_Pinduoduo_btn], [simple_Poizon_btn, main_menu_btn]])
samples_Pinduoduo_keyboard = create_inline_keyboard([[simple_1688_btn, simple_Taobao_btn], [simple_Poizon_btn, main_menu_btn]])
samples_Poizon_keyboard = create_inline_keyboard([[simple_1688_btn, simple_Taobao_btn], [simple_Pinduoduo_btn, main_menu_btn]])

data_updated_keyboard = create_inline_keyboard([[my_profile_btn], [main_menu_btn]])

admin_keyboard = create_inline_keyboard([[add_track_codes_btn], [track_codes_list_btn],
                                         [recreate_db_btn], [recreate_tc_btn]])
