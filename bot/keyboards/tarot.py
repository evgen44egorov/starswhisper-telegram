from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

TAROT_SPREADS = {
    "🃏 Один вопрос": "Один вопрос",
    "💌 Расклад на отношения": "Расклад на отношения",
    "🔮 Расклад на ситуацию": "Расклад на ситуацию",
    "⚖️ Расклад выбора": "Расклад выбора",
}

TAROT_AREAS = {
    "💌 Любовь": "Любовь и отношения",
    "💼 Работа": "Работа и карьера",
    "💰 Деньги": "Деньги",
    "🌱 Личный путь": "Самопознание и личный путь",
}

CONFIRM_TAROT_BUTTON = "✨ Получить расклад"
PAY_TAROT_BUTTON = "⭐ Перейти к оплате"
RESTART_TAROT_BUTTON = "✏️ Выбрать заново"
CANCEL_TAROT_BUTTON = "↩️ Отмена"


def tarot_spread_keyboard() -> ReplyKeyboardMarkup:
    labels = list(TAROT_SPREADS)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in labels[:2]],
            [KeyboardButton(text=label) for label in labels[2:]],
            [KeyboardButton(text=CANCEL_TAROT_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def tarot_area_keyboard() -> ReplyKeyboardMarkup:
    labels = list(TAROT_AREAS)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in labels[:2]],
            [KeyboardButton(text=label) for label in labels[2:]],
            [KeyboardButton(text=CANCEL_TAROT_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def tarot_confirmation_keyboard(payments_enabled: bool) -> ReplyKeyboardMarkup:
    action = PAY_TAROT_BUTTON if payments_enabled else CONFIRM_TAROT_BUTTON
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=action)],
            [
                KeyboardButton(text=RESTART_TAROT_BUTTON),
                KeyboardButton(text=CANCEL_TAROT_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def tarot_needs_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Заполнить профиль", callback_data="start:profile")],
            [InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data="tarot:cancel")],
        ]
    )
