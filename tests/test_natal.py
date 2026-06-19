import unittest

from bot.keyboards.natal import (
    natal_life_stage_keyboard,
    natal_hour_keyboard,
    natal_minute_ones_keyboard,
    natal_minute_tens_keyboard,
    natal_subfocus_keyboard,
    natal_time_accuracy_keyboard,
    natal_time_period_keyboard,
)
from bot.texts.ru import NATAL_CONFIRM_TEXT


class NatalKeyboardTests(unittest.TestCase):
    def test_hour_keyboard_contains_every_hour_and_unknown(self) -> None:
        callbacks = {
            button.callback_data
            for row in natal_hour_keyboard().inline_keyboard
            for button in row
        }
        self.assertTrue({f"natal:hour:{hour}" for hour in range(24)} <= callbacks)
        self.assertIn("natal:time_unknown", callbacks)

    def test_minute_keyboards_allow_exact_minute(self) -> None:
        tens_callbacks = {
            button.callback_data
            for row in natal_minute_tens_keyboard().inline_keyboard
            for button in row
        }
        ones_callbacks = {
            button.callback_data
            for row in natal_minute_ones_keyboard(0).inline_keyboard
            for button in row
        }
        self.assertTrue({f"natal:minute_tens:{value}" for value in range(6)} <= tens_callbacks)
        self.assertTrue({f"natal:minute_ones:{value}" for value in range(10)} <= ones_callbacks)

    def test_personalization_steps_are_button_only(self) -> None:
        keyboards = [
            natal_time_accuracy_keyboard(has_saved_time=True),
            natal_time_period_keyboard(),
            natal_life_stage_keyboard(),
            natal_subfocus_keyboard("career"),
        ]
        callbacks = {
            button.callback_data
            for keyboard in keyboards
            for row in keyboard.inline_keyboard
            for button in row
        }
        self.assertIn("natal:accuracy:exact", callbacks)
        self.assertIn("natal:period:morning", callbacks)
        self.assertIn("natal:life:changes", callbacks)
        self.assertIn("natal:subfocus:change", callbacks)

    def test_confirmation_has_single_birth_time_line(self) -> None:
        self.assertIn("Время рождения: {time_details}", NATAL_CONFIRM_TEXT)
        self.assertNotIn("Точность времени:", NATAL_CONFIRM_TEXT)
        self.assertNotIn("Время суток:", NATAL_CONFIRM_TEXT)


if __name__ == "__main__":
    unittest.main()
