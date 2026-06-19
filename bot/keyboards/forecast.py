from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def forecast_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Создать прогноз",
                    callback_data="forecast:generate",
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Вернуться в меню",
                    callback_data="forecast:cancel",
                )
            ],
        ]
    )


def forecast_needs_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Заполнить профиль",
                    callback_data="start:profile",
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Вернуться в меню",
                    callback_data="forecast:cancel",
                )
            ],
        ]
    )

