import calendar
from datetime import date

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
UNKNOWN_PARTNER_DATE_BUTTON = "🤷 Не знаю дату"
SKIP_PARTNER_PLACE_BUTTON = "⏭ Пропустить место"
CONFIRM_COMPATIBILITY_BUTTON = "✨ Получить тестовый разбор"
PAY_COMPATIBILITY_BUTTON = "⭐ Перейти к оплате"
RESTART_COMPATIBILITY_BUTTON = "✏️ Заполнить заново"
CANCEL_COMPATIBILITY_BUTTON = "↩️ Отмена"

YEAR_PAGE_SIZE = 16
MONTH_NAMES = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)


def initial_partner_year_page() -> int:
    current_year = date.today().year
    return max(current_year - 120, ((current_year - 46) // YEAR_PAGE_SIZE) * YEAR_PAGE_SIZE)


def partner_year_keyboard(page_start: int) -> InlineKeyboardMarkup:
    current_year = date.today().year
    minimum_year = current_year - 120
    page_start = max(minimum_year, min(page_start, current_year))
    years = range(page_start, min(page_start + YEAR_PAGE_SIZE, current_year + 1))
    buttons = [
        InlineKeyboardButton(text=str(year), callback_data=f"compatibility:year:{year}")
        for year in years
    ]
    rows = [buttons[index:index + 4] for index in range(0, len(buttons), 4)]
    navigation = []
    if page_start > minimum_year:
        navigation.append(InlineKeyboardButton(
            text="⬅️ Раньше",
            callback_data=f"compatibility:years:{max(minimum_year, page_start - YEAR_PAGE_SIZE)}",
        ))
    if page_start + YEAR_PAGE_SIZE <= current_year:
        navigation.append(InlineKeyboardButton(
            text="Позже ➡️",
            callback_data=f"compatibility:years:{page_start + YEAR_PAGE_SIZE}",
        ))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(
        text=UNKNOWN_PARTNER_DATE_BUTTON,
        callback_data="compatibility:date_unknown",
    )])
    rows.append([InlineKeyboardButton(text=CANCEL_COMPATIBILITY_BUTTON, callback_data="compatibility:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def partner_month_keyboard(year: int) -> InlineKeyboardMarkup:
    today = date.today()
    last_month = today.month if year == today.year else 12
    buttons = [
        InlineKeyboardButton(text=MONTH_NAMES[month - 1], callback_data=f"compatibility:month:{month}")
        for month in range(1, last_month + 1)
    ]
    rows = [buttons[index:index + 3] for index in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text=UNKNOWN_PARTNER_DATE_BUTTON, callback_data="compatibility:date_unknown")])
    rows.append([InlineKeyboardButton(text="↩️ К выбору года", callback_data="compatibility:year_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def partner_day_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    days = calendar.monthrange(year, month)[1]
    today = date.today()
    if year == today.year and month == today.month:
        days = min(days, today.day)
    buttons = [
        InlineKeyboardButton(text=str(day), callback_data=f"compatibility:day:{day}")
        for day in range(1, days + 1)
    ]
    rows = [buttons[index:index + 7] for index in range(0, len(buttons), 7)]
    rows.append([InlineKeyboardButton(text=UNKNOWN_PARTNER_DATE_BUTTON, callback_data="compatibility:date_unknown")])
    rows.append([InlineKeyboardButton(text="↩️ К выбору месяца", callback_data="compatibility:month_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
