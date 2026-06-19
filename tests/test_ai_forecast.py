import unittest
from datetime import date

from bot.config import Settings
from bot.database.models import Profile
from bot.services.ai import AstrobotAIService
from bot.services.prompts import (
    build_compatibility_input,
    build_daily_forecast_input,
    build_monthly_forecast_input,
    build_natal_chart_input,
    build_numerology_input,
    build_personal_question_input,
    build_tarot_input,
)
from bot.utils.months import first_day_of_next_month, format_month_period
from bot.utils.question import normalize_question
from bot.utils.safety import is_crisis_question
from bot.utils.zodiac import get_zodiac_sign


class ZodiacTests(unittest.TestCase):
    def test_zodiac_boundaries(self) -> None:
        self.assertEqual(get_zodiac_sign(date(1990, 3, 20)), "Рыбы")
        self.assertEqual(get_zodiac_sign(date(1990, 3, 21)), "Овен")
        self.assertEqual(get_zodiac_sign(date(1990, 12, 22)), "Козерог")


class ForecastPromptTests(unittest.TestCase):
    def test_profile_values_are_serialized_as_data(self) -> None:
        profile = Profile(
            name="Анна",
            birth_date=date(1996, 8, 14),
            birth_place="Тбилиси, Грузия",
        )
        prompt = build_daily_forecast_input(profile, date(2026, 6, 18))
        self.assertIn('"имя": "Анна"', prompt)
        self.assertIn('"солнечный_знак": "Лев"', prompt)

    def test_question_is_serialized_as_data(self) -> None:
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        prompt = build_personal_question_input(
            profile,
            "Работа",
            "Как лучше обсудить новую роль?",
            date(2026, 6, 18),
        )
        self.assertIn('"сфера_вопроса": "Работа"', prompt)
        self.assertIn('"вопрос": "Как лучше обсудить новую роль?"', prompt)

    def test_compatibility_profiles_are_serialized(self) -> None:
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        prompt = build_compatibility_input(
            profile=profile,
            relationship_type="Романтические",
            partner_name="Михаил",
            partner_birth_date=date(1995, 3, 21),
            partner_birth_time=None,
            partner_birth_place=None,
            current_date=date(2026, 6, 18),
        )
        self.assertIn('"солнечный_знак": "Лев"', prompt)
        self.assertIn('"солнечный_знак": "Овен"', prompt)
        self.assertIn('"тип_отношений": "Романтические"', prompt)

    def test_compatibility_allows_unknown_partner_date(self) -> None:
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        prompt = build_compatibility_input(
            profile=profile,
            relationship_type="Романтические",
            partner_name="Михаил",
            partner_birth_date=None,
            partner_birth_time=None,
            partner_birth_place=None,
            current_date=date(2026, 6, 18),
        )
        self.assertIn('"дата_рождения": "не указано"', prompt)
        self.assertIn('"солнечный_знак": "не определён"', prompt)

    def test_monthly_period_and_area_are_serialized(self) -> None:
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        prompt = build_monthly_forecast_input(
            profile,
            "июль 2026",
            "Работа",
            date(2026, 6, 18),
        )
        self.assertIn('"период": "июль 2026"', prompt)
        self.assertIn('"главный_фокус": "Работа"', prompt)

    def test_natal_data_and_focus_are_serialized(self) -> None:
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        prompt = build_natal_chart_input(
            profile=profile,
            focus="Работа и реализация",
            subfocus="Смена работы",
            life_stage="Переживаю перемены",
            time_accuracy="Время неизвестно",
            time_period="Утро, 06:00–11:59",
            current_date=date(2026, 6, 19),
        )
        self.assertIn('"солнечный_знак": "Лев"', prompt)
        self.assertIn('"главный_фокус": "Работа и реализация"', prompt)
        self.assertIn('"время_рождения": "неизвестно"', prompt)
        self.assertIn('"уточнение_фокуса": "Смена работы"', prompt)
        self.assertIn('"текущий_жизненный_этап": "Переживаю перемены"', prompt)

    def test_tarot_cards_are_serialized_as_data(self) -> None:
        profile = Profile(name="Анна", birth_date=date(1992, 11, 25))
        cards = [
            {"position": "Текущая ситуация", "card": "Звезда", "orientation": "прямое"},
            {"position": "Скрытое влияние", "card": "Луна", "orientation": "перевёрнутое"},
            {"position": "Совет", "card": "Сила", "orientation": "прямое"},
        ]
        prompt = build_tarot_input(
            profile,
            "Расклад на ситуацию",
            "Работа и карьера",
            "Стоит ли менять направление работы?",
            cards,
            date(2026, 6, 19),
        )
        self.assertIn('"card": "Звезда"', prompt)
        self.assertIn('"orientation": "перевёрнутое"', prompt)
        self.assertIn('"солнечный_знак": "Стрелец"', prompt)

    def test_numerology_uses_precalculated_numbers(self) -> None:
        prompt = build_numerology_input(
            profile=Profile(name="Анна", birth_date=date(1992, 11, 25)),
            period="Прогноз на текущий год",
            numbers={"life_path": 3, "personal_year": 1},
            current_date=date(2026, 6, 19),
        )
        self.assertIn('"life_path": 3', prompt)
        self.assertIn('"personal_year": 1', prompt)


class DemoForecastTests(unittest.IsolatedAsyncioTestCase):
    async def test_demo_forecast_is_personalized_and_deterministic(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        service = AstrobotAIService(settings)

        first = await service.generate_daily_forecast(profile, date(2026, 6, 18))
        second = await service.generate_daily_forecast(profile, date(2026, 6, 18))

        self.assertTrue(first.is_demo)
        self.assertIn("Анна", first.text)
        self.assertIn("Лев", first.text)
        self.assertEqual(first.text, second.text)

    async def test_demo_personal_question(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        result = await AstrobotAIService(settings).generate_personal_question(
            profile,
            "Работа",
            "Как лучше обсудить новую роль?",
            date(2026, 6, 18),
        )
        self.assertTrue(result.is_demo)
        self.assertIn("Как лучше обсудить новую роль?", result.text)

    async def test_demo_compatibility(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        result = await AstrobotAIService(settings).generate_compatibility(
            profile=profile,
            relationship_type="Романтические",
            partner_name="Михаил",
            partner_birth_date=date(1995, 3, 21),
            partner_birth_time=None,
            partner_birth_place=None,
            current_date=date(2026, 6, 18),
        )
        self.assertTrue(result.is_demo)
        self.assertIn("Анна и Михаил", result.text)
        self.assertIn("Лев", result.text)
        self.assertIn("Овен", result.text)

    async def test_demo_compatibility_without_partner_date(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        result = await AstrobotAIService(settings).generate_compatibility(
            profile=profile,
            relationship_type="Романтические",
            partner_name="Михаил",
            partner_birth_date=None,
            partner_birth_time=None,
            partner_birth_place=None,
            current_date=date(2026, 6, 18),
        )
        self.assertIn("Дата рождения Михаил не указана", result.text)

    async def test_demo_monthly_forecast(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        result = await AstrobotAIService(settings).generate_monthly_forecast(
            profile,
            "июль 2026",
            "Работа",
            date(2026, 6, 18),
        )
        self.assertTrue(result.is_demo)
        self.assertIn("июль 2026", result.text)
        self.assertIn("Работа", result.text)

    async def test_demo_natal_chart(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        profile = Profile(name="Анна", birth_date=date(1996, 8, 14))
        result = await AstrobotAIService(settings).generate_natal_chart(
            profile=profile,
            focus="Самопознание и рост",
            subfocus="Личные границы",
            life_stage="Ищу опору и ясность",
            time_accuracy="Время неизвестно",
            time_period=None,
            current_date=date(2026, 6, 19),
        )
        self.assertTrue(result.is_demo)
        self.assertIn("Натальная карта для Анна", result.text)
        self.assertIn("Самопознание и рост", result.text)
        self.assertIn("Личные границы", result.text)
        self.assertIn("точные положения планет", result.text.lower())

    async def test_demo_tarot_uses_drawn_cards(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        cards = [
            {"position": "Текущая ситуация", "card": "Звезда", "orientation": "прямое"},
            {"position": "Скрытое влияние", "card": "Луна", "orientation": "перевёрнутое"},
            {"position": "Совет", "card": "Сила", "orientation": "прямое"},
        ]
        result = await AstrobotAIService(settings).generate_tarot_reading(
            profile=Profile(name="Анна", birth_date=date(1992, 11, 25)),
            spread="Расклад на ситуацию",
            area="Работа и карьера",
            question="Стоит ли менять направление работы?",
            cards=cards,
            current_date=date(2026, 6, 19),
        )
        self.assertTrue(result.is_demo)
        self.assertIn("Звезда", result.text)
        self.assertIn("Луна", result.text)
        self.assertIn("Сила", result.text)

    async def test_demo_numerology_uses_calculated_cycles(self) -> None:
        settings = Settings(
            BOT_TOKEN="test-token-longer-than-20-characters",
            AI_PROVIDER="demo",
            _env_file=None,
        )
        numbers = {
            "life_path": 3,
            "birthday_number": 7,
            "personal_year": 1,
            "personal_month": 7,
            "personal_day": 8,
        }
        result = await AstrobotAIService(settings).generate_numerology(
            profile=Profile(name="Анна", birth_date=date(1992, 11, 25)),
            period="Прогноз на текущий год",
            numbers=numbers,
            current_date=date(2026, 6, 19),
        )
        self.assertTrue(result.is_demo)
        self.assertIn("Число жизненного пути — 3", result.text)
        self.assertIn("Личный год — 1", result.text)


class QuestionSafetyTests(unittest.TestCase):
    def test_validates_question_length(self) -> None:
        self.assertEqual(
            normalize_question("  Как   мне лучше поступить?  "),
            "Как мне лучше поступить?",
        )
        with self.assertRaises(ValueError):
            normalize_question("Коротко")

    def test_detects_crisis_phrases(self) -> None:
        self.assertTrue(is_crisis_question("Я не хочу жить и не знаю, что делать"))
        self.assertFalse(is_crisis_question("Стоит ли менять работу в этом году?"))


class MonthHelpersTests(unittest.TestCase):
    def test_next_month_crosses_year_boundary(self) -> None:
        self.assertEqual(
            first_day_of_next_month(date(2026, 12, 15)),
            date(2027, 1, 1),
        )
        self.assertEqual(format_month_period(date(2027, 1, 1)), "январь 2027")


if __name__ == "__main__":
    unittest.main()
