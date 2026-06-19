from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

NUMEROLOGY_PERIODS = {
    "🔢 Базовый портрет": "Базовый нумерологический портрет",
    "☀️ На сегодня": "Прогноз на сегодня",
    "🌙 На текущий месяц": "Прогноз на текущий месяц",
    "🗓 На текущий год": "Прогноз на текущий год",
}

CONFIRM_NUMEROLOGY_BUTTON = "✨ Получить тестовый разбор"
PAY_NUMEROLOGY_BUTTON = "⭐ Перейти к оплате"
RESTART_NUMEROLOGY_BUTTON = "✏️ Выбрать заново"
CANCEL_NUMEROLOGY_BUTTON = "↩️ Отмена"


def numerology_period_keyboard() -> ReplyKeyboardMarkup:
    labels = list(NUMEROLOGY_PERIODS)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0])],
            [KeyboardButton(text=labels[1]), KeyboardButton(text=labels[2])],
            [KeyboardButton(text=labels[3])],
            [KeyboardButton(text=CANCEL_NUMEROLOGY_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def numerology_confirmation_keyboard(payments_enabled: bool) -> ReplyKeyboardMarkup:
    action = PAY_NUMEROLOGY_BUTTON if payments_enabled else CONFIRM_NUMEROLOGY_BUTTON
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=action)],
            [
                KeyboardButton(text=RESTART_NUMEROLOGY_BUTTON),
                KeyboardButton(text=CANCEL_NUMEROLOGY_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def numerology_needs_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Заполнить профиль", callback_data="start:profile")],
            [InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data="numerology:cancel")],
        ]
    )
