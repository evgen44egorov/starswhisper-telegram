from datetime import date


def get_zodiac_sign(birth_date: date) -> str:
    month_day = (birth_date.month, birth_date.day)
    boundaries = [
        ((1, 20), "Козерог"),
        ((2, 19), "Водолей"),
        ((3, 21), "Рыбы"),
        ((4, 20), "Овен"),
        ((5, 21), "Телец"),
        ((6, 21), "Близнецы"),
        ((7, 23), "Рак"),
        ((8, 23), "Лев"),
        ((9, 23), "Дева"),
        ((10, 23), "Весы"),
        ((11, 22), "Скорпион"),
        ((12, 22), "Стрелец"),
        ((12, 32), "Козерог"),
    ]
    for boundary, sign in boundaries:
        if month_day < boundary:
            return sign
    return "Козерог"


def get_zodiac_element(sign: str) -> str:
    elements = {
        "Овен": "Огонь",
        "Лев": "Огонь",
        "Стрелец": "Огонь",
        "Телец": "Земля",
        "Дева": "Земля",
        "Козерог": "Земля",
        "Близнецы": "Воздух",
        "Весы": "Воздух",
        "Водолей": "Воздух",
        "Рак": "Вода",
        "Скорпион": "Вода",
        "Рыбы": "Вода",
    }
    return elements[sign]
