import unittest
from datetime import date, time

from bot.utils.profile import (
    normalize_birth_place,
    normalize_name,
    parse_birth_date,
    parse_birth_time,
)


class ProfileValidationTests(unittest.TestCase):
    def test_normalizes_name_and_place(self) -> None:
        self.assertEqual(normalize_name("  Анна   Мария  "), "Анна Мария")
        self.assertEqual(
            normalize_birth_place("  Тбилиси,   Грузия  "),
            "Тбилиси, Грузия",
        )

    def test_parses_valid_birth_date(self) -> None:
        result = parse_birth_date("14.08.1996", today=date(2026, 6, 18))
        self.assertEqual(result, date(1996, 8, 14))

    def test_rejects_invalid_or_future_birth_date(self) -> None:
        with self.assertRaises(ValueError):
            parse_birth_date("31.02.2000", today=date(2026, 6, 18))
        with self.assertRaises(ValueError):
            parse_birth_date("19.06.2026", today=date(2026, 6, 18))

    def test_parses_and_validates_birth_time(self) -> None:
        self.assertEqual(parse_birth_time("08:30"), time(8, 30))
        with self.assertRaises(ValueError):
            parse_birth_time("25:10")


if __name__ == "__main__":
    unittest.main()

