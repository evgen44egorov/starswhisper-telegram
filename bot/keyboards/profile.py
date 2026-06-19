from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

UNKNOWN_TIME_BUTTON = "⏭ Не знаю время"
SKIP_PLACE_BUTTON = "⏭ Пропустить место"
CONFIRM_PROFILE_BUTTON = "✅ Сохранить профиль"
RESTART_PROFILE_BUTTON = "✏️ Заполнить заново"
CANCEL_BUTTON = "↩️ Отмена"


def time_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=UNKNOWN_TIME_BUTTON)],
            [KeyboardButton(text=CANCEL_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Например: 08:30",
    )


def place_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_PLACE_BUTTON)],
            [KeyboardButton(text=CANCEL_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Например: Тбилиси, Грузия",
    )


def profile_confirmation_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CONFIRM_PROFILE_BUTTON)],
            [
                KeyboardButton(text=RESTART_PROFILE_BUTTON),
                KeyboardButton(text=CANCEL_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def profile_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить данные", callback_data="profile:edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔮 Получить прогноз", callback_data="start:forecast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить профиль", callback_data="profile:delete"
                )
            ],
        ]
    )


def profile_delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить", callback_data="profile:delete_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Нет, оставить", callback_data="profile:delete_cancel"
                )
            ],
        ]
    )

