from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

FORECAST_BUTTON = "🔮 Мой прогноз"
QUESTION_BUTTON = "💌 Задать вопрос"
COMPATIBILITY_BUTTON = "🧩 Совместимость"
NATAL_BUTTON = "🪐 Натальная карта"
MONTH_BUTTON = "🌙 Прогноз на месяц"
PROFILE_BUTTON = "👤 Мой профиль"
ORDERS_BUTTON = "📦 Мои заказы"
HELP_BUTTON = "🛟 Помощь"


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Получить прогноз", callback_data="start:forecast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔮 Посмотреть услуги", callback_data="start:services"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Заполнить профиль", callback_data="start:profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Мои заказы", callback_data="orders:list"
                )
            ],
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=FORECAST_BUTTON), KeyboardButton(text=QUESTION_BUTTON)],
            [
                KeyboardButton(text=COMPATIBILITY_BUTTON),
                KeyboardButton(text=NATAL_BUTTON),
            ],
            [KeyboardButton(text=MONTH_BUTTON), KeyboardButton(text=PROFILE_BUTTON)],
            [KeyboardButton(text=ORDERS_BUTTON), KeyboardButton(text=HELP_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )


def services_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔮 Личный прогноз", callback_data="service:forecast"
                ),
                InlineKeyboardButton(
                    text="💌 Личный вопрос", callback_data="service:question"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧩 Совместимость", callback_data="service:compatibility"
                ),
                InlineKeyboardButton(
                    text="🪐 Натальная карта", callback_data="service:natal"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌙 Прогноз на месяц", callback_data="service:month"
                )
            ],
        ]
    )
