from aiogram.types import InlineKeyboardMarkup

from keyboards.common_keyboards import (
    create_keyboard,
    create_keyboard_button,
    create_inline_button,
    create_inline_keyboard
)


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
def get_admin_edit_user_keyboard(
        internal_user_id: int,
        has_username: bool,
        has_phone: bool
) -> InlineKeyboardMarkup:

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
