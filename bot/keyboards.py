from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

from filters_and_config import admin_ids


# --- Вспомогательные функции ---

def create_keyboard_button(text: str) -> KeyboardButton:
    """Создаёт кнопку для обычной клавиатуры."""
    return KeyboardButton(text=text)


def create_keyboard(buttons: list[list[KeyboardButton]], resize: bool = True) -> ReplyKeyboardMarkup:
    """Создаёт обычную клавиатуру с заданными кнопками."""
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=resize)


def create_inline_button(text: str, callback_data: str = None, url: str = None) -> InlineKeyboardButton:
    """Создаёт инлайн-кнопку с текстом и callback_data или URL."""
    if url: return InlineKeyboardButton(text=text, url=url)
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру с заданными кнопками."""
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Клавиатуры главного меню
main_menu_buttons = [
    ["Адрес склада", "Бланк для заказа"],
    ["Где брать трек-номер", "Консолидация"],
    ["Проверка трек-кода", "Проверка товаров"],
    ["Рассчитать объём", "Рассчитать страховку"],
    ["Тарифы", "Упаковка"]
]  # "Запрещённые товары"

main_keyboard = create_keyboard([[create_keyboard_button(text) for text in row] for row in main_menu_buttons])


# Инлайн кнопки главного меню
def get_main_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру главного меню с учётом прав администратора."""
    is_admin = user_id in admin_ids
    main_inline_buttons = [
        [
            create_inline_button("Админ", callback_data="admin_panel" if is_admin else None,
                                 url="https://t.me/fir2201" if not is_admin else None),
            create_inline_button("Курс Alipay", url="https://t.me/Alipay_Chat_ru")
        ],
        [
            create_inline_button("Мой профиль", callback_data="my_profile"),
            create_inline_button("Чат Карго FS-33", url="https://t.me/cargoFS33")
        ]
    ]

    return create_inline_keyboard(main_inline_buttons)


# Админ-панель
admin_buttons = [
    ["Список трек-кодов", "Изменить данные"],
    ["️Добавить пребывшие на склад трек-коды"],
    ["Добавить отправленные трек-коды"],
    ["Удалить отправленные трек-коды"],
    ["Искать инфо по ID", "Вернуться в главное меню"]
]

admin_keyboard = create_keyboard([[create_keyboard_button(text) for text in row] for row in admin_buttons])

# Кнопки связи с админами
contact_admin_keyboard = create_inline_keyboard(
    [
        [create_inline_button(text="👤 Главный админ (Фируз)", url="https://t.me/fir2201")],
        [create_inline_button(text="⚙️ Технический админ (Абдулхамид)", url="https://t.me/abdulhamidgulov")]
    ]
)

# Кнопки подтверждения действий
yes_btn = create_inline_button(text="✅ Да", callback_data="danger_confirm")
no_btn = create_inline_button(text="❌ Нет", callback_data="danger_cancel")

confirm_keyboard = create_inline_keyboard([[yes_btn, no_btn]])


# Кнопки регистрации
skip_registration_btn = create_inline_button("️Пропустить", "pass_reg")
start_registration_btn = create_inline_button("️Пройти регистрацию", "do_reg")
reg_keyboard = create_inline_keyboard([[skip_registration_btn, start_registration_btn]])

# Кнопки профиля
my_track_codes_btn = create_inline_button("️Мои трек коды", "my_track_codes")
edit_profile_data_btn = create_inline_button("️Изменить данные", "change_profile_data")
my_profile_keyboard = create_inline_keyboard([[edit_profile_data_btn, my_track_codes_btn]])

# Кнопки изменений данных профиля
change_name_btn = create_inline_button("Имя и фамилию", "change_name")
change_phone_btn = create_inline_button("Телефон", "change_phone")
change_data_keyboard = create_inline_keyboard([[change_name_btn], [change_phone_btn]])


# Кнопки образцов
sample_buttons = {
    "1688": create_inline_button("️Образец 1688", "simple_1688"),
    "Taobao": create_inline_button("️Образец Taobao", "simple_Taobao"),
    "Pinduoduo": create_inline_button("️Образец Pinduoduo", "simple_Pinduoduo"),
    "Poizon": create_inline_button("️Образец Poizon", "simple_Poizon")
}


def create_samples_keyboard(exclude: str = None) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру для образцов, исключая указанную кнопку, если нужно."""
    buttons = [btn for key, btn in sample_buttons.items() if key != exclude]
    keyboard_layout = [[btn] for btn in buttons] if exclude else [buttons[:2], buttons[2:]]
    return create_inline_keyboard(keyboard_layout)


# Кнопки, где брать трек номера
where_get_buttons = {
    "1688": create_inline_button("С 1688", "where_get_with_1688"),
    "Taobao": create_inline_button("С Taobao", "where_get_with_Taobao"),
    "Pinduoduo": create_inline_button("С Pinduoduo", "where_get_with_Pinduoduo"),
    "Poizon": create_inline_button("С Poizon", "where_get_with_Poizon")
}

where_get_keyboard = create_inline_keyboard([
    [where_get_buttons["1688"], where_get_buttons["Taobao"]],
    [where_get_buttons["Pinduoduo"], where_get_buttons["Poizon"]]
])

# Кнопка отмена в добавление трек-номеров
cancel_keyboard = create_keyboard([[create_keyboard_button("Отмена")]])

# Кнопки выбора типа товаров
item_type_buttons = [
    ["Продукты", "Одежда", "Обувь"],
    ["Электроника", "Хозтовары"],
    ["Сборный груз",  "Мебель"]
]
item_type_keyboard = create_keyboard([[create_keyboard_button(text) for text in row] for row in item_type_buttons])
