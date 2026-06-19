from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import start_keyboard
from bot.services.screens import show_screen
from bot.texts.ru import WELCOME_TEXT

router = Router(name="start")


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(message, WELCOME_TEXT, reply_markup=start_keyboard())
