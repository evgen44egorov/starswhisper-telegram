import unittest
from datetime import date, time

from bot.database.models import Profile
from bot.handlers import profile as profile_handler
from bot.handlers.profile import profile_text
from bot.keyboards.profile import (
    birth_day_keyboard,
    birth_month_keyboard,
    birth_year_keyboard,
    initial_birth_year_page,
)


def callbacks(keyboard) -> set[str | None]:
    return {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    }


class ProfileDateKeyboardTests(unittest.TestCase):
    def test_profile_date_prompts_are_connected_to_handler(self) -> None:
        self.assertTrue(profile_handler.PROFILE_YEAR_PROMPT)
        self.assertTrue(profile_handler.PROFILE_MONTH_PROMPT)
        self.assertTrue(profile_handler.PROFILE_DAY_PROMPT)

    def test_year_keyboard_has_navigation_and_year_choices(self) -> None:
        page = initial_birth_year_page()
        values = callbacks(birth_year_keyboard(page))
        self.assertIn(f"profile:year:{page}", values)
        self.assertTrue(any(value and value.startswith("profile:years:") for value in values))

    def test_month_and_day_are_selected_with_buttons(self) -> None:
        self.assertIn("profile:month:12", callbacks(birth_month_keyboard(1992)))
        leap_days = callbacks(birth_day_keyboard(1992, 2))
        regular_days = callbacks(birth_day_keyboard(1993, 2))
        self.assertIn("profile:day:29", leap_days)
        self.assertNotIn("profile:day:29", regular_days)

    def test_general_profile_no_longer_displays_birth_time(self) -> None:
        profile = Profile(
            name="Анна",
            birth_date=date(1992, 11, 25),
            birth_time=time(1, 30),
            birth_place="Санкт-Петербург, Россия",
        )
        text = profile_text(profile)
        self.assertNotIn("Время рождения", text)
        self.assertIn("25.11.1992", text)


if __name__ == "__main__":
    unittest.main()
