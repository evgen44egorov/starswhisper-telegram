import calendar
from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

SKIP_PLACE_BUTTON = "⏭ Пропустить место"
CONFIRM_PROFILE_BUTTON = "✅ Сохранить профиль"
RESTART_PROFILE_BUTTON = "✏️ Заполнить заново"
CANCEL_BUTTON = "↩️ Отмена"


YEAR_PAGE_SIZE = 16
MONTH_NAMES = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)


def initial_birth_year_page() -> int:
    current_year = date.today().year
    return max(current_year - 120, ((current_year - 46) // YEAR_PAGE_SIZE) * YEAR_PAGE_SIZE)


def birth_year_keyboard(page_start: int) -> InlineKeyboardMarkup:
    current_year = date.today().year
    minimum_year = current_year - 120
    page_start = max(minimum_year, min(page_start, current_year))
    years = [year for year in range(page_start, min(page_start + YEAR_PAGE_SIZE, current_year + 1))]
    rows = [
        [
            InlineKeyboardButton(text=str(year), callback_data=f"profile:year:{year}")
            for year in years[index : index + 4]
        ]
        for index in range(0, len(years), 4)
    ]
    navigation = []
    if page_start > minimum_year:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Раньше",
                callback_data=f"profile:years:{max(minimum_year, page_start - YEAR_PAGE_SIZE)}",
            )
        )
    if page_start + YEAR_PAGE_SIZE <= current_year:
        navigation.append(
            InlineKeyboardButton(
                text="Позже ➡️",
                callback_data=f"profile:years:{page_start + YEAR_PAGE_SIZE}",
            )
        )
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(text="↩️ Отмена", callback_data="profile:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def birth_month_keyboard(year: int) -> InlineKeyboardMarkup:
    today = date.today()
    last_month = today.month if year == today.year else 12
    buttons = [
        InlineKeyboardButton(
            text=MONTH_NAMES[month - 1],
            callback_data=f"profile:month:{month}",
        )
        for month in range(1, last_month + 1)
    ]
    rows = [buttons[index : index + 3] for index in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="↩️ К выбору года", callback_data="profile:year_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def birth_day_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    days = calendar.monthrange(year, month)[1]
    today = date.today()
    if year == today.year and month == today.month:
        days = min(days, today.day)
    buttons = [
        InlineKeyboardButton(text=str(day), callback_data=f"profile:day:{day}")
        for day in range(1, days + 1)
    ]
    rows = [buttons[index : index + 7] for index in range(0, len(buttons), 7)]
    rows.append([InlineKeyboardButton(text="↩️ К выбору месяца", callback_data="profile:month_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
