from keyboards import create_inline_button, create_inline_keyboard, create_keyboard_button, create_keyboard

calculate_volume_btn = create_inline_button(text="Рассчитать обьём", callback_data="calculate_volume")
calculate_shipping_btn = create_inline_button(text="Рассчитать доставку", callback_data="calc_shipping")

calc_main_menu_keyboard = create_inline_keyboard([
    [calculate_volume_btn],
    [calculate_shipping_btn]
])

bulk_cargo_btn = create_keyboard_button("Объёмный груз")
clothing_btn = create_keyboard_button("Одежда")
fabric_btn = create_keyboard_button("Ткань")
laptops_btn = create_keyboard_button("Ноутбуки")
phones_btn = create_keyboard_button("Телефоны")
food_btn = create_keyboard_button("Продукты")
electronics_btn = create_keyboard_button("Электроника")
pharmacy_btn = create_keyboard_button("Аптека")


item_type_keyboard = create_keyboard([
    [bulk_cargo_btn, electronics_btn],
    [laptops_btn, phones_btn, pharmacy_btn],
    [clothing_btn, fabric_btn, food_btn]
])
