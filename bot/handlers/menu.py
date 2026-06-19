from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards.main_menu import (
    HELP_BUTTON,
    main_menu_keyboard,
    services_keyboard,
)
from bot.services.payments import public_price_label
from bot.services.screens import show_screen
from bot.texts.ru import HELP_TEXT, SERVICES_TEXT

router = Router(name="menu")


def services_text() -> str:
    settings = get_settings()
    return SERVICES_TEXT.format(
        monthly_price=public_price_label("monthly_forecast", settings),
        question_price=public_price_label("personal_question", settings),
        compatibility_price=public_price_label("compatibility", settings),
        natal_price=public_price_label("natal_chart", settings),
        numerology_price=public_price_label("numerology", settings),
        tarot_price=public_price_label("tarot_astrology", settings),
    )


@router.callback_query(F.data == "start:services")
async def services_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message, services_text(), reply_markup=services_keyboard()
        )


@router.callback_query(F.data.startswith("service:"))
async def service_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            services_text(),
            reply_markup=services_keyboard(),
        )


@router.message(F.text == HELP_BUTTON)
async def help_menu(message: Message) -> None:
    await show_screen(message, HELP_TEXT, reply_markup=main_menu_keyboard())
