import random
import unittest

from bot.keyboards.main_menu import TAROT_BUTTON, main_menu_keyboard, services_keyboard
from bot.keyboards.tarot import TAROT_AREAS, TAROT_SPREADS, tarot_area_keyboard, tarot_spread_keyboard
from bot.services.tarot import MAJOR_ARCANA, draw_tarot_cards


class TarotTests(unittest.TestCase):
    def test_draws_three_unique_persistable_cards(self) -> None:
        cards = draw_tarot_cards(rng=random.Random(42))
        self.assertEqual(len(cards), 3)
        self.assertEqual(len({card["card"] for card in cards}), 3)
        self.assertTrue(all(card["card"] in MAJOR_ARCANA for card in cards))
        self.assertTrue(all(card["orientation"] in {"прямое", "перевёрнутое"} for card in cards))

    def test_tarot_is_available_in_both_menus(self) -> None:
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
        self.assertIn(TAROT_BUTTON, reply_labels)
        self.assertIn("service:tarot", inline_callbacks)

    def test_tarot_reply_keyboards_contain_keyboard_buttons(self) -> None:
        spread_labels = {
            button.text
            for row in tarot_spread_keyboard().keyboard
            for button in row
        }
        area_labels = {
            button.text
            for row in tarot_area_keyboard().keyboard
            for button in row
        }
        self.assertTrue(set(TAROT_SPREADS) <= spread_labels)
        self.assertTrue(set(TAROT_AREAS) <= area_labels)


if __name__ == "__main__":
    unittest.main()
