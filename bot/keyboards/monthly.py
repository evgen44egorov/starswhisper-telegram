from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

CURRENT_MONTH_BUTTON = "🌒 Текущий месяц"
NEXT_MONTH_BUTTON = "🌕 Следующий месяц"
MONTH_PERIODS = {CURRENT_MONTH_BUTTON, NEXT_MONTH_BUTTON}

GENERAL_MONTH_AREA = "✨ Общий прогноз"
LOVE_MONTH_AREA = "💌 Любовь"
WORK_MONTH_AREA = "💼 Работа"
MONEY_MONTH_AREA = "💰 Деньги"
EMOTIONS_MONTH_AREA = "🧘 Эмоциональное состояние"

MONTH_AREAS = {
    GENERAL_MONTH_AREA: "Общий месяц",
    LOVE_MONTH_AREA: "Любовь",
    WORK_MONTH_AREA: "Работа",
    MONEY_MONTH_AREA: "Деньги",
    EMOTIONS_MONTH_AREA: "Эмоциональное состояние",
}

CONFIRM_MONTHLY_BUTTON = "✨ Получить тестовый прогноз"
PAY_MONTHLY_BUTTON = "⭐ Перейти к оплате"
RESTART_MONTHLY_BUTTON = "✏️ Выбрать заново"
CANCEL_MONTHLY_BUTTON = "↩️ Отмена"


def month_period_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CURRENT_MONTH_BUTTON)],
            [KeyboardButton(text=NEXT_MONTH_BUTTON)],
            [KeyboardButton(text=CANCEL_MONTHLY_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def month_area_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=GENERAL_MONTH_AREA)],
            [KeyboardButton(text=LOVE_MONTH_AREA), KeyboardButton(text=WORK_MONTH_AREA)],
            [
                KeyboardButton(text=MONEY_MONTH_AREA),
                KeyboardButton(text=EMOTIONS_MONTH_AREA),
            ],
            [KeyboardButton(text=CANCEL_MONTHLY_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def monthly_confirmation_keyboard(payments_enabled: bool = False) -> ReplyKeyboardMarkup:
    confirm_text = PAY_MONTHLY_BUTTON if payments_enabled else CONFIRM_MONTHLY_BUTTON
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=confirm_text)],
            [
                KeyboardButton(text=RESTART_MONTHLY_BUTTON),
                KeyboardButton(text=CANCEL_MONTHLY_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def monthly_needs_profile_keyboard() -> InlineKeyboardMarkup:
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
                    callback_data="monthly:cancel",
                )
            ],
        ]
    )
