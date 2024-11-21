from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_button(text: str, callback_data: str = None, url: str = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data, url=url)

def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=buttons)

checking_track_code_btn = create_button("️Проверка трек кода🔎", "checking_track_code")
price_btn = create_button("️Цены 💲", "price")
warehouse_address_btn = create_button("️Адрес складов🗺", "warehouse_address")
prohibited_goods_btn = create_button("️Запрещённые товары ❌", "prohibited_goods")
my_profile_btn = create_button("️Мой профиль👤", "my_profile")

pass_reg_btn = create_button("️Пропустить", "pass_reg")
do_reg_btn = create_button("️Пройти регистрацию", "do_reg")

change_name_btn = create_button("Изменит имя и фамилию", "change_name")
change_number_btn = create_button("️Изменить телефон", "change_number")
change_address_btn = create_button("️Изменит адрес", "change_address")
my_track_code_btn = create_button("️Мои трек коды", "my_track_code")
main_menu_btn = create_button("️Назад в главное меню", "main_menu")

main_keyboard = create_inline_keyboard([[checking_track_code_btn],
                                        [price_btn, warehouse_address_btn],
                                        [prohibited_goods_btn, my_profile_btn]])

reg_keyboard = create_inline_keyboard([[pass_reg_btn, do_reg_btn]])

my_profile_keyboard = create_inline_keyboard([[change_name_btn, change_number_btn],
                                              [change_address_btn, my_track_code_btn],
                                              [main_menu_btn]])

back_to_menu_keyboard = create_inline_keyboard([[main_menu_btn]])
