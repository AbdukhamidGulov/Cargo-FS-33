from logging import getLogger

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BotCommand, BotCommandScopeAllPrivateChats
from aiogram.exceptions import TelegramForbiddenError

from database.db_info_content import get_info_content
from database.db_users import get_user_by_tg_id
from keyboards.user_keyboards import main_keyboard, get_main_inline_keyboard, reg_keyboard
from utils.fsm_guard import clear_state_for_global_command

commands_router = Router()
logger = getLogger(__name__)


async def set_default_commands(bot):
    commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом / Перезапустить"),
        BotCommand(command="help", description="❓ Получить помощь и информацию"),
        BotCommand(command="admin", description="💬 Связаться с администраторами."),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
    logger.info("Стандартные команды бота установлены.")


photo_cache = {}


async def get_cached_content(key: str) -> str:
    """Получает значение из кэша или базы данных, если его нет в кэше."""
    if key not in photo_cache:
        photo_cache[key] = await get_info_content(key)
    return photo_cache[key]


@commands_router.message(CommandStart())
@commands_router.message(F.text == "Вернуться в главное меню")
async def start_command(message: Message, state: FSMContext):
    """Обрабатывает /start и возврат в главное меню."""
    was_in_state = await clear_state_for_global_command(state)
    if was_in_state:
        logger.info("FSM состояние сброшено через /start. tg_id=%s", message.from_user.id)

    main_menu_photo = await get_cached_content("main_menu_photo")

    try:
        await message.answer_photo(
            photo=main_menu_photo,
            caption="Вас приветствует Telegram-бот карго компании <b>FS-33</b> 🚚"
        )

        user = await get_user_by_tg_id(message.from_user.id)

        if user:
            await message.answer(
                "Я помогу вам найти адреса складов, проверить трек-код и ознакомить с ценами",
                reply_markup=main_keyboard
            )
            await message.answer(
                "Как я могу вам помочь?",
                reply_markup=get_main_inline_keyboard(message.from_user.id)
            )
        else:
            await message.answer(
                "Вы ещё не зарегистрированы, чтобы пользоваться нашим ботом\n\n"
                "Хотите зарегистрироваться?",
                reply_markup=reg_keyboard
            )

    except TelegramForbiddenError:
        logger.warning(
            "Невозможно отправить стартовое сообщение пользователю tg_id=%s: бот заблокирован пользователем",
            message.from_user.id
        )
        return


@commands_router.message(Command("help"))
async def help_command(message: Message, state: FSMContext):
    """Обрабатывает команду /help."""
    was_in_state = await clear_state_for_global_command(state)
    if was_in_state:
        logger.info("FSM состояние сброшено через /help. tg_id=%s", message.from_user.id)

    help_text = (
        "Я бот карго компании FS-33. Вот что я могу:\n\n"
        "🚀 /start - Перезапустить бота и вернуться в главное меню.\n"
        "❓ /help - Показать это сообщение с помощью.\n"
        "🔑 /admin - Связь с администраторами.\n\n"
        "Также в главном меню вы найдёте кнопки для:\n"
        "- Информации о складах и услугах\n"
        "- Калькулятора для расчёта объема, страховки и стоимости доставки\n"
        "- Вашего профиля"
    )
    await message.answer(help_text)


@commands_router.message(Command("myid"))
async def myid_command(message: Message):
    """Обрабатывает команду /myid."""
    await message.answer(f"Ваш id: <code>{message.from_user.id}</code>")
