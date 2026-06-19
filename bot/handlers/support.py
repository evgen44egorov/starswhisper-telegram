from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import get_settings
from bot.keyboards.main_menu import main_menu_keyboard
from bot.services.admin import notify_admin
from bot.services.screens import show_screen
from bot.texts.ru import PAYSUPPORT_TEXT, SUPPORT_TEXT, TERMS_TEXT

router = Router(name="support")


def support_contact() -> str:
    username = (get_settings().support_username or "").strip().lstrip("@")
    if not username:
        return "Контакт поддержки пока не указан: бот работает в тестовом режиме."
    return f"Контакт поддержки: @{escape(username)}"


@router.message(Command("terms"))
async def terms_command(message: Message) -> None:
    await show_screen(message, TERMS_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("support"))
async def support_command(message: Message) -> None:
    if message.from_user is not None:
        await notify_admin(
            message.bot,
            "🛟 <b>Запрос поддержки</b>\n\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n"
            "Команда: /support",
        )
    await show_screen(
        message,
        SUPPORT_TEXT.format(contact=support_contact()),
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("paysupport"))
async def paysupport_command(message: Message) -> None:
    if message.from_user is not None:
        await notify_admin(
            message.bot,
            "⭐ <b>Запрос по оплате</b>\n\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n"
            "Команда: /paysupport",
        )
    await show_screen(
        message,
        PAYSUPPORT_TEXT.format(contact=support_contact()),
        reply_markup=main_menu_keyboard(),
    )
