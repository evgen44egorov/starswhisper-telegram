import secrets
from random import Random

MAJOR_ARCANA = (
    "Шут",
    "Маг",
    "Верховная Жрица",
    "Императрица",
    "Император",
    "Иерофант",
    "Влюблённые",
    "Колесница",
    "Сила",
    "Отшельник",
    "Колесо Фортуны",
    "Справедливость",
    "Повешенный",
    "Смерть",
    "Умеренность",
    "Дьявол",
    "Башня",
    "Звезда",
    "Луна",
    "Солнце",
    "Суд",
    "Мир",
)

CARD_POSITIONS = ("Текущая ситуация", "Скрытое влияние", "Совет")


def draw_tarot_cards(count: int = 3, rng: Random | None = None) -> list[dict[str, str]]:
    generator = rng or secrets.SystemRandom()
    cards = generator.sample(MAJOR_ARCANA, count)
    return [
        {
            "position": CARD_POSITIONS[index] if index < len(CARD_POSITIONS) else f"Карта {index + 1}",
            "card": card,
            "orientation": generator.choice(("прямое", "перевёрнутое")),
        }
        for index, card in enumerate(cards)
    ]
