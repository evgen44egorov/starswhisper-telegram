from datetime import date

MASTER_NUMBERS = {11, 22, 33}


def reduce_number(value: int) -> int:
    number = abs(value)
    while number > 9 and number not in MASTER_NUMBERS:
        number = sum(int(digit) for digit in str(number))
    return number


def calculate_numerology(birth_date: date, target_date: date) -> dict[str, int]:
    life_path = reduce_number(sum(int(digit) for digit in birth_date.strftime("%d%m%Y")))
    birthday_number = reduce_number(birth_date.day)
    personal_year = reduce_number(
        birth_date.day
        + birth_date.month
        + sum(int(digit) for digit in str(target_date.year))
    )
    personal_month = reduce_number(personal_year + target_date.month)
    personal_day = reduce_number(personal_month + target_date.day)
    return {
        "life_path": life_path,
        "birthday_number": birthday_number,
        "personal_year": personal_year,
        "personal_month": personal_month,
        "personal_day": personal_day,
    }
