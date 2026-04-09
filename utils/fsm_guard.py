from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.user_keyboards import main_menu_buttons, cancel_keyboard


GLOBAL_EXIT_COMMANDS = {"/start", "/help", "/admin"}

MAIN_MENU_TEXTS = {
    text
    for row in main_menu_buttons
    for text in row
}
MAIN_MENU_TEXTS.add("Вернуться в главное меню")


async def clear_state_for_global_command(state: FSMContext) -> bool:
    """
    Очищает текущее FSM-состояние, если оно активно.
    Возвращает True, если состояние было очищено.
    """
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        return True
    return False


async def warn_if_user_is_inside_fsm(message: Message, state: FSMContext) -> bool:
    """
    Если пользователь находится внутри FSM и нажал кнопку главного меню,
    не сбрасывает состояние, а предупреждает, что нужно выйти через Отмена или /start.
    Возвращает True, если предупреждение было отправлено.
    """
    current_state = await state.get_state()

    if not current_state:
        return False

    if not message.text:
        return False

    text = message.text.strip()

    if text in MAIN_MENU_TEXTS:
        await message.answer(
            "ℹ️ Сейчас вы находитесь в незавершённом действии.\n\n"
            "Сначала нажмите <b>Отмена</b> или используйте команду <code>/start</code>, "
            "чтобы выйти из текущего процесса и перейти в другой раздел.",
            reply_markup=cancel_keyboard
        )
        return True

    return False
