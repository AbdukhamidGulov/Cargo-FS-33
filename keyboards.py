from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

from filters_and_config import admin_ids


# ************************************************************
# ОБЩИЕ ФУНКЦИИ
# ************************************************************

def create_keyboard_button(text: str) -> KeyboardButton:
    """Создаёт кнопку для обычной клавиатуры."""
    return KeyboardButton(text=text)


def create_keyboard(buttons: list[list[KeyboardButton]], resize: bool = True, selective: bool = False) -> ReplyKeyboardMarkup:
    """Создаёт обычную клавиатуру с заданными кнопками."""
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=resize, selective=selective)


def create_inline_button(text: str, callback_data: str = None, url: str = None) -> InlineKeyboardButton:
    """Создаёт инлайн-кнопку с текстом и callback_data или URL."""
    if url: return InlineKeyboardButton(text=text, url=url)
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def create_inline_keyboard(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру с заданными кнопками."""
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ************************************************************
# КЛАВИАТУРЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ************************************************************

# Клавиатуры главного меню (Reply Keyboard)
main_menu_buttons = [
    ["Адрес склада", "Бланк для Заказа"],
    ["Бланк для Таможни", "Где брать трек-номер"],
    ["Добавить трек-кода", "Калькулятор объёма"],
    ["Консолидация", "Проверка трек-кодов"],
    ["Проверка товаров", "Тарифы"]
]

main_keyboard = create_keyboard([[create_keyboard_button(text) for text in row] for row in main_menu_buttons])


# Инлайн кнопки главного меню (Админ/Профиль/Чаты)
def get_main_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру главного меню с учётом прав администратора."""
    is_admin = user_id in admin_ids
    main_inline_buttons = [
        [
            # Кнопка "Админ" либо ведет в админку, либо на контакт админа
            create_inline_button("Админ", callback_data="admin_panel" if is_admin else None,
                                 url="https://t.me/fir2201" if not is_admin else None),
            create_inline_button("Курс Alipay", url="https://t.me/Alipay_Chat_ru")
        ],
        [
            create_inline_button("Мой профиль", callback_data="my_profile"),
            create_inline_button("Страхование", callback_data="insurance"),
        ],
        [
            create_inline_button("Упаковка", callback_data="packing"),
            create_inline_button("Чат Карго FS-33", url="https://t.me/cargoFS33")
        ]
    ]

    return create_inline_keyboard(main_inline_buttons)


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

# Кнопки образцов (Inline)
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


# Кнопки, где брать трек номера (Inline)
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

# Кнопка "Отмена" для FSM (Reply Keyboard)
cancel_keyboard = create_keyboard([[create_keyboard_button("Отмена")]])

# Кнопки выбора типа товаров (Reply Keyboard)
item_type_buttons = [
    ["Продукты", "Одежда", "Обувь"],
    ["Электроника", "Хозтовары"],
    ["Сборный груз", "Мебель"]
]
item_type_keyboard = create_keyboard([[create_keyboard_button(text) for text in row] for row in item_type_buttons])

# Кнопки после успешного добавления трек-кодов (Inline)
add_more_codes_btn = create_inline_button("➕ Добавить ещё трек-коды", "add_more_track_codes")
check_codes_btn = create_inline_button("🔎 Проверить статус трек-кода", "start_check_codes")

add_track_codes_follow_up_keyboard = create_inline_keyboard([
    [add_more_codes_btn],
    [check_codes_btn, my_track_codes_btn]
])


# ************************************************************
# КЛАВИАТУРЫ ДЛЯ АДМИНОВ
# ************************************************************

# Админ-панель (Reply Keyboard)
admin_buttons = [
    ["Список трек-кодов", "Изменить данные"],
    ["Массовая привязка трек-кодов"],
    ["️Добавить прибывшие на склад трек-коды"],
    ["Добавить отправленные трек-коды"],
    ["Добавить прибывшие посылки", "Найти владельца трек-кода"],
    ["Искать инфо по ID", "Удалить трек-коды"],
    ["Удалить отправленные трек-коды", "Вернуться в главное меню"]
]

admin_keyboard = create_keyboard([[create_keyboard_button(text) for text in row] for row in admin_buttons])

# Кнопки связи с админами (Inline)
contact_admin_keyboard = create_inline_keyboard(
    [
        [create_inline_button(text="👤 Главный админ (Фируз)", url="https://t.me/fir2201")],
        [create_inline_button(text="Админ (Иван)", url="https://t.me/cargooFS33")],
        [create_inline_button(text="Админ (Дарья)", url="https://t.me/FS_Admin33")],
        [create_inline_button(text="⚙️ Разработчик бота (Абдулхамид)", url="https://t.me/abdulhamidgulov")]
    ]
)

# Кнопки подтверждения действий (Inline)
yes_btn = create_inline_button(text="✅ Да", callback_data="danger_confirm")
no_btn = create_inline_button(text="❌ Нет", callback_data="danger_cancel")

confirm_keyboard = create_inline_keyboard([[yes_btn, no_btn]])


# Функция для редактирования пользователя (Inline)
def get_admin_edit_user_keyboard(internal_user_id: int, has_username: bool, has_phone: bool) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для админа для редактирования данных пользователя.
    """
    # Меняем текст кнопки в зависимости от того, есть ли данные
    username_text = "Изменить никнейм" if has_username else "Добавить никнейм"
    phone_text = "Изменить телефон" if has_phone else "Добавить телефон"

    # Создаем кнопки
    username_btn = create_inline_button(
        text=f"👤 {username_text}",
        callback_data=f"admin_edit_username:{internal_user_id}"
    )
    phone_btn = create_inline_button(
        text=f"📞 {phone_text}",
        callback_data=f"admin_edit_phone:{internal_user_id}"
    )

    buttons = [
        [username_btn],
        [phone_btn]
    ]

    return create_inline_keyboard(buttons)


# --- НОВАЯ ФУНКЦИЯ: Клавиатура для заказа ---

def get_order_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора действия после добавления товара в заказ."""
    return create_inline_keyboard([
        [create_inline_button("➕ Добавить ещё товар", "order_add_next")],
        [create_inline_button("✅ Закончить и получить Excel", "order_finish")]
    ])
