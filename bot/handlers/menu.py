from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import (
    HELP_BUTTON,
    NATAL_BUTTON,
    main_menu_keyboard,
    services_keyboard,
)
from bot.services.screens import show_screen
from bot.texts.ru import HELP_TEXT, SERVICE_STUBS, SERVICES_TEXT

router = Router(name="menu")


@router.callback_query(F.data == "start:services")
async def services_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message, SERVICES_TEXT, reply_markup=services_keyboard()
        )


@router.callback_query(F.data.startswith("service:"))
async def service_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    service = callback.data.split(":", maxsplit=1)[1] if callback.data else ""
    text = SERVICE_STUBS.get(service, SERVICES_TEXT)
    if isinstance(callback.message, Message):
        await show_screen(callback.message, text, reply_markup=main_menu_keyboard())


@router.message(F.text == NATAL_BUTTON)
async def natal_menu(message: Message) -> None:
    await show_screen(
        message, SERVICE_STUBS["natal"], reply_markup=main_menu_keyboard()
    )


@router.message(F.text == HELP_BUTTON)
async def help_menu(message: Message) -> None:
    await show_screen(message, HELP_TEXT, reply_markup=main_menu_keyboard())
