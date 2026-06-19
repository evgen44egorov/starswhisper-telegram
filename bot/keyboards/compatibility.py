from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

ROMANTIC_TYPE = "💞 Романтические"
FRIEND_TYPE = "🤝 Дружеские"
BUSINESS_TYPE = "💼 Деловые"
FAMILY_TYPE = "🏡 Семейные"
UNSURE_TYPE = "🧭 Пока не знаю"

RELATIONSHIP_TYPES = {
    ROMANTIC_TYPE: "Романтические",
    FRIEND_TYPE: "Дружеские",
    BUSINESS_TYPE: "Деловые",
    FAMILY_TYPE: "Семейные",
    UNSURE_TYPE: "Пока не определены",
}

UNKNOWN_PARTNER_TIME_BUTTON = "⏭ Не знаю время"
SKIP_PARTNER_PLACE_BUTTON = "⏭ Пропустить место"
CONFIRM_COMPATIBILITY_BUTTON = "✨ Получить тестовый разбор"
PAY_COMPATIBILITY_BUTTON = "⭐ Перейти к оплате"
RESTART_COMPATIBILITY_BUTTON = "✏️ Заполнить заново"
CANCEL_COMPATIBILITY_BUTTON = "↩️ Отмена"


def relationship_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ROMANTIC_TYPE), KeyboardButton(text=FRIEND_TYPE)],
            [KeyboardButton(text=BUSINESS_TYPE), KeyboardButton(text=FAMILY_TYPE)],
            [KeyboardButton(text=UNSURE_TYPE)],
            [KeyboardButton(text=CANCEL_COMPATIBILITY_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выбери тип отношений",
    )


def partner_time_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=UNKNOWN_PARTNER_TIME_BUTTON)],
            [KeyboardButton(text=CANCEL_COMPATIBILITY_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Например: 08:30",
    )


def partner_place_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_PARTNER_PLACE_BUTTON)],
            [KeyboardButton(text=CANCEL_COMPATIBILITY_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Например: Батуми, Грузия",
    )


def compatibility_confirmation_keyboard(
    payments_enabled: bool = False,
) -> ReplyKeyboardMarkup:
    confirm_text = (
        PAY_COMPATIBILITY_BUTTON
        if payments_enabled
        else CONFIRM_COMPATIBILITY_BUTTON
    )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=confirm_text)],
            [
                KeyboardButton(text=RESTART_COMPATIBILITY_BUTTON),
                KeyboardButton(text=CANCEL_COMPATIBILITY_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def compatibility_needs_profile_keyboard() -> InlineKeyboardMarkup:
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
                    callback_data="compatibility:cancel",
                )
            ],
        ]
    )
