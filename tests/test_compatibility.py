import unittest

from bot.keyboards.compatibility import (
    UNKNOWN_PARTNER_DATE_BUTTON,
    initial_partner_year_page,
    partner_day_keyboard,
    partner_month_keyboard,
    partner_year_keyboard,
)


class CompatibilityDateKeyboardTests(unittest.TestCase):
    def test_year_picker_contains_years_navigation_and_unknown_date(self) -> None:
        keyboard = partner_year_keyboard(initial_partner_year_page())
        buttons = [button for row in keyboard.inline_keyboard for button in row]
        self.assertTrue(any((button.callback_data or "").startswith("compatibility:year:") for button in buttons))
        self.assertTrue(any(button.text == UNKNOWN_PARTNER_DATE_BUTTON for button in buttons))

    def test_month_and_day_are_selected_with_buttons(self) -> None:
        month_keyboard = partner_month_keyboard(1992)
        day_keyboard = partner_day_keyboard(1992, 2)
        month_callbacks = {
            button.callback_data
            for row in month_keyboard.inline_keyboard
            for button in row
        }
        day_callbacks = {
            button.callback_data
            for row in day_keyboard.inline_keyboard
            for button in row
        }
        self.assertIn("compatibility:month:11", month_callbacks)
        self.assertIn("compatibility:day:29", day_callbacks)
        self.assertIn("compatibility:date_unknown", month_callbacks)
        self.assertIn("compatibility:date_unknown", day_callbacks)


if __name__ == "__main__":
    unittest.main()
