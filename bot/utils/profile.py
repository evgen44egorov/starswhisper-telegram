import re
from datetime import date, datetime, time


def normalize_name(value: str) -> str:
    name = " ".join(value.strip().split())
    if not 2 <= len(name) <= 50:
        raise ValueError("Имя должно содержать от 2 до 50 символов.")
    return name


def parse_birth_date(value: str, today: date | None = None) -> date:
    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value.strip()):
        raise ValueError("Укажи дату в формате ДД.ММ.ГГГГ.")

    try:
        birth_date = datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        raise ValueError("Такой даты не существует. Проверь день, месяц и год.") from None

    current_date = today or date.today()
    if birth_date > current_date:
        raise ValueError("Дата рождения не может быть в будущем.")

    try:
        earliest_date = current_date.replace(year=current_date.year - 120)
    except ValueError:
        earliest_date = current_date.replace(
            year=current_date.year - 120,
            day=28,
        )

    if birth_date < earliest_date:
        raise ValueError("Проверь год рождения: сейчас он выглядит необычно.")

    return birth_date


def parse_birth_time(value: str) -> time:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value.strip()):
        raise ValueError("Укажи время в формате ЧЧ:ММ, например 08:30.")
    return datetime.strptime(value.strip(), "%H:%M").time()


def normalize_birth_place(value: str) -> str:
    place = " ".join(value.strip().split())
    if not 2 <= len(place) <= 100:
        raise ValueError("Место рождения должно содержать от 2 до 100 символов.")
    return place

