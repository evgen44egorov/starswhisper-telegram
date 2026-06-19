import unittest
from datetime import date

from bot.keyboards.main_menu import NUMEROLOGY_BUTTON, main_menu_keyboard, services_keyboard
from bot.keyboards.numerology import NUMEROLOGY_PERIODS, numerology_period_keyboard
from bot.services.numerology import calculate_numerology, reduce_number


class NumerologyTests(unittest.TestCase):
    def test_reduces_numbers_and_preserves_master_numbers(self) -> None:
        self.assertEqual(reduce_number(38), 11)
        self.assertEqual(reduce_number(29), 11)
        self.assertEqual(reduce_number(39), 3)

    def test_calculates_known_personal_cycles(self) -> None:
        numbers = calculate_numerology(date(1992, 11, 25), date(2026, 6, 19))
        self.assertEqual(
            numbers,
            {
                "life_path": 3,
                "birthday_number": 7,
                "personal_year": 1,
                "personal_month": 7,
                "personal_day": 8,
            },
        )

    def test_numerology_is_button_driven_and_visible_in_menus(self) -> None:
        period_labels = {
            button.text
            for row in numerology_period_keyboard().keyboard
            for button in row
        }
        reply_labels = {
            button.text
            for row in main_menu_keyboard().keyboard
            for button in row
        }
        inline_callbacks = {
            button.callback_data
            for row in services_keyboard().inline_keyboard
            for button in row
        }
        self.assertTrue(set(NUMEROLOGY_PERIODS) <= period_labels)
        self.assertIn(NUMEROLOGY_BUTTON, reply_labels)
        self.assertIn("service:numerology", inline_callbacks)


if __name__ == "__main__":
    unittest.main()
