from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

NATAL_FOCUSES = {
    "full": "Полная карта",
    "relationships": "Любовь и отношения",
    "career": "Работа и реализация",
    "money": "Деньги и ценность",
    "growth": "Самопознание и рост",
}

NATAL_TIME_ACCURACY = {
    "exact": "Точное время из документа",
    "approximate": "Примерное время, ±15 минут",
    "period": "Известно только время суток",
    "unknown": "Время неизвестно",
}

NATAL_TIME_PERIODS = {
    "night": "Ночь, 00:00–05:59",
    "morning": "Утро, 06:00–11:59",
    "day": "День, 12:00–17:59",
    "evening": "Вечер, 18:00–23:59",
}

NATAL_LIFE_STAGES = {
    "new": "Начинаю новый этап",
    "changes": "Переживаю перемены",
    "decision": "Принимаю важное решение",
    "clarity": "Ищу опору и ясность",
    "stable": "Стабильный период, изучаю себя",
}

NATAL_SUBFOCUSES = {
    "full": {
        "balance": "Баланс всех сфер",
        "strengths": "Сильные стороны",
        "direction": "Жизненное направление",
    },
    "relationships": {
        "search": "Поиск отношений",
        "current": "Текущие отношения",
        "difficult": "Сложный период",
        "after": "После расставания",
    },
    "career": {
        "direction": "Выбор направления",
        "change": "Смена работы",
        "growth": "Карьерный рост",
        "project": "Собственный проект",
        "team": "Отношения с коллективом",
    },
    "money": {
        "stability": "Финансовая стабильность",
        "income": "Рост дохода",
        "habits": "Денежные привычки",
        "anxiety": "Тревога о деньгах",
    },
    "growth": {
        "esteem": "Самооценка",
        "boundaries": "Личные границы",
        "emotions": "Эмоции и реакции",
        "direction": "Поиск своего направления",
    },
}


def natal_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Данные верны", callback_data="natal:use_profile")],
            [InlineKeyboardButton(text="🕐 Уточнить время", callback_data="natal:change_time")],
            [InlineKeyboardButton(text="👤 Изменить профиль", callback_data="start:profile")],
            [InlineKeyboardButton(text="↩️ Отмена", callback_data="natal:cancel")],
        ]
    )


def natal_hour_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for start in range(0, 24, 6):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{hour:02d}",
                    callback_data=f"natal:hour:{hour}",
                )
                for hour in range(start, start + 6)
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="❔ Время неизвестно", callback_data="natal:time_unknown")]
    )
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="natal:restart")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def natal_time_accuracy_keyboard(has_saved_time: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_saved_time:
        rows.extend(
            [
                [InlineKeyboardButton(text="📄 Точное из документа", callback_data="natal:accuracy:exact")],
                [InlineKeyboardButton(text="🕐 Примерное, ±15 минут", callback_data="natal:accuracy:approximate")],
            ]
        )
    rows.extend(
        [
            [InlineKeyboardButton(text="🌗 Знаю только время суток", callback_data="natal:accuracy:period")],
            [InlineKeyboardButton(text="❔ Время неизвестно", callback_data="natal:accuracy:unknown")],
            [InlineKeyboardButton(text="✏️ Выбрать точное время", callback_data="natal:change_time")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="natal:restart")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def natal_time_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌙 Ночь", callback_data="natal:period:night")],
            [InlineKeyboardButton(text="🌅 Утро", callback_data="natal:period:morning")],
            [InlineKeyboardButton(text="☀️ День", callback_data="natal:period:day")],
            [InlineKeyboardButton(text="🌆 Вечер", callback_data="natal:period:evening")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="natal:accuracy_back")],
        ]
    )


def natal_life_stage_keyboard() -> InlineKeyboardMarkup:
    icons = {"new": "🌱", "changes": "🔄", "decision": "⚖️", "clarity": "🧘", "stable": "✨"}
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{icons[key]} {label}", callback_data=f"natal:life:{key}")]
            for key, label in NATAL_LIFE_STAGES.items()
        ]
        + [[InlineKeyboardButton(text="↩️ Проверить данные", callback_data="natal:restart")]]
    )


def natal_minute_tens_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{value}0–{value}9",
                    callback_data=f"natal:minute_tens:{value}",
                )
                for value in range(3)
            ],
            [
                InlineKeyboardButton(
                    text=f"{value}0–{value}9",
                    callback_data=f"natal:minute_tens:{value}",
                )
                for value in range(3, 6)
            ],
            [InlineKeyboardButton(text="↩️ К выбору часа", callback_data="natal:change_time")],
        ]
    )


def natal_minute_ones_keyboard(tens: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{tens}{value}",
            callback_data=f"natal:minute_ones:{value}",
        )
        for value in range(10)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[:5],
            buttons[5:],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="natal:minute_back")],
        ]
    )


def natal_focus_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Полная карта", callback_data="natal:focus:full")],
            [
                InlineKeyboardButton(
                    text="💌 Отношения", callback_data="natal:focus:relationships"
                ),
                InlineKeyboardButton(text="💼 Работа", callback_data="natal:focus:career"),
            ],
            [
                InlineKeyboardButton(text="💰 Деньги", callback_data="natal:focus:money"),
                InlineKeyboardButton(text="🌱 Рост", callback_data="natal:focus:growth"),
            ],
            [InlineKeyboardButton(text="↩️ Проверить данные", callback_data="natal:restart")],
        ]
    )


def natal_subfocus_keyboard(focus: str) -> InlineKeyboardMarkup:
    choices = NATAL_SUBFOCUSES.get(focus, NATAL_SUBFOCUSES["full"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"natal:subfocus:{key}")]
            for key, label in choices.items()
        ]
        + [[InlineKeyboardButton(text="↩️ К выбору темы", callback_data="natal:focus_back")]]
    )


def natal_confirmation_keyboard(payments_enabled: bool) -> InlineKeyboardMarkup:
    action = "⭐ Перейти к оплате" if payments_enabled else "✨ Получить карту"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=action, callback_data="natal:confirm")],
            [InlineKeyboardButton(text="✏️ Изменить выбор", callback_data="natal:restart")],
            [InlineKeyboardButton(text="↩️ Отмена", callback_data="natal:cancel")],
        ]
    )


def natal_needs_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Заполнить профиль", callback_data="start:profile")],
            [InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data="natal:cancel")],
        ]
    )
