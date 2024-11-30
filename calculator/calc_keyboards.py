from keyboards import create_button, create_inline_keyboard

calculate_volume_btn = create_button(text="Рассчитать обьём", callback_data="calculate_volume")
calculate_shipping_btn = create_button(text="Рассчитать доставку", callback_data="calc_shipping")
# calculate_redemption_btn = create_button(text="Рассчитать выкуп", callback_data="calculate_redemption")
# _btn = create_button(text="", callback_data="")
# _btn = create_button(text="", callback_data="")
# _btn = create_button(text="", callback_data="")
# _btn = create_button(text="", callback_data="")
# _btn = create_button(text="", callback_data="")

# back_btn = create_button(text="Назад", callback_data="back")

calc_main_menu_keyboard = create_inline_keyboard([[calculate_volume_btn],
                                                  [calculate_shipping_btn]])  # [calculate_redemption_btn],
