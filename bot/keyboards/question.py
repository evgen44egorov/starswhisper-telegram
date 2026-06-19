from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

LOVE_AREA = "💌 Любовь"
WORK_AREA = "💼 Работа"
MONEY_AREA = "💰 Деньги"
SELF_AREA = "🧘 Саморазвитие"
FAMILY_AREA = "🏡 Семья"
OTHER_AREA = "🧭 Другое"

QUESTION_AREAS = {
    LOVE_AREA: "Любовь",
    WORK_AREA: "Работа",
    MONEY_AREA: "Деньги",
    SELF_AREA: "Саморазвитие",
    FAMILY_AREA: "Семья",
    OTHER_AREA: "Другое",
}

CANCEL_QUESTION_BUTTON = "↩️ Отмена"
CONFIRM_QUESTION_BUTTON = "✨ Получить тестовый ответ"
PAY_QUESTION_BUTTON = "⭐ Перейти к оплате"
EDIT_QUESTION_BUTTON = "✏️ Изменить вопрос"


def question_area_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=LOVE_AREA), KeyboardButton(text=WORK_AREA)],
            [KeyboardButton(text=MONEY_AREA), KeyboardButton(text=SELF_AREA)],
            [KeyboardButton(text=FAMILY_AREA), KeyboardButton(text=OTHER_AREA)],
            [KeyboardButton(text=CANCEL_QUESTION_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выбери сферу вопроса",
    )


def question_confirmation_keyboard(payments_enabled: bool = False) -> ReplyKeyboardMarkup:
    confirm_text = PAY_QUESTION_BUTTON if payments_enabled else CONFIRM_QUESTION_BUTTON
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=confirm_text)],
            [
                KeyboardButton(text=EDIT_QUESTION_BUTTON),
                KeyboardButton(text=CANCEL_QUESTION_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def question_needs_profile_keyboard() -> InlineKeyboardMarkup:
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
                    callback_data="question:cancel",
                )
            ],
        ]
    )
