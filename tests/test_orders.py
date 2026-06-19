import unittest
from datetime import datetime

from bot.database.models import Order
from bot.handlers.orders import extract_order_id
from bot.services.orders import format_order_card, format_order_input, parse_order_input
from bot.services.results import format_order_result_chunks


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

    def test_formats_natal_order_input(self) -> None:
        order = make_order(
            service_code="natal_chart",
            input_data_json=(
                '{"profile":{"birth_date":"1996-08-14","birth_time":"09:07",'
                '"birth_place":"Тбилиси"},"focus":"Работа и реализация"}'
            ),
        )
        text = format_order_input(order)
        self.assertIn("09:07", text)
        self.assertIn("Работа и реализация", text)

    def test_long_result_is_split_without_losing_footer(self) -> None:
        order = make_order(service_code="natal_chart", public_id="N-LONG")
        chunks = format_order_result_chunks(order, ("Большой раздел <карты>. " * 500))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 4096 for chunk in chunks))
        self.assertIn("N-LONG", chunks[-1])
        self.assertTrue(any("&lt;карты&gt;" in chunk for chunk in chunks))

    def test_formats_tarot_order_with_drawn_cards(self) -> None:
        order = make_order(
            service_code="tarot_astrology",
            input_data_json=(
                '{"spread":"Расклад на ситуацию","area":"Работа",'
                '"question":"Стоит ли менять работу?","cards":['
                '{"card":"Звезда"},{"card":"Луна"},{"card":"Сила"}]}'
            ),
        )
        card = format_order_card(order)
        self.assertIn("Таро + астрология", card)
        self.assertIn("Звезда, Луна, Сила", card)


if __name__ == "__main__":
    unittest.main()
