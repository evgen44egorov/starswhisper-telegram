import unittest
from datetime import datetime

from bot.database.models import Order
from bot.handlers.orders import extract_order_id
from bot.services.orders import format_order_card, parse_order_input


def make_order(**overrides: object) -> Order:
    values: dict[str, object] = {
        "id": 7,
        "public_id": "Q-ABC123",
        "user_id": 1,
        "service_code": "personal_question",
        "status": "test_completed",
        "price_stars": 350,
        "currency": "XTR",
        "input_data_json": '{"area":"Работа","question":"Как обсудить новую роль?"}',
        "result_text": "Готовый ответ",
        "created_at": datetime(2026, 6, 18, 12, 30),
        "updated_at": datetime(2026, 6, 18, 12, 31),
    }
    values.update(overrides)
    return Order(**values)


class OrderFormattingTests(unittest.TestCase):
    def test_formats_question_order(self) -> None:
        card = format_order_card(make_order())
        self.assertIn("Q-ABC123", card)
        self.assertIn("Личный вопрос", card)
        self.assertIn("Как обсудить новую роль?", card)
        self.assertIn("не списывалась", card)

    def test_handles_invalid_input_json(self) -> None:
        order = make_order(input_data_json="not-json")
        self.assertEqual(parse_order_input(order), {})

    def test_extracts_and_rejects_callback_ids(self) -> None:
        self.assertEqual(extract_order_id("orders:view:42"), 42)
        self.assertIsNone(extract_order_id("orders:view:wrong"))
        self.assertIsNone(extract_order_id(None))


if __name__ == "__main__":
    unittest.main()

