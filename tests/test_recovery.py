import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.database.models import Order
from bot.services.ai import AIResult
from bot.services.recovery import recover_paid_orders


def make_recoverable():
    order = Order(
        id=7,
        public_id="Q-RECOVER",
        user_id=1,
        service_code="personal_question",
        status="recovering",
        price_stars=1,
        currency="XTR",
        input_data_json="{}",
        created_at=datetime(2026, 6, 19, 12, 0),
        updated_at=datetime(2026, 6, 19, 12, 0),
    )
    return SimpleNamespace(order=order, telegram_id=123456)


class RecoveryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovers_and_delivers_result(self) -> None:
        bot = AsyncMock()
        result = AIResult(
            text="Готовый результат",
            provider="openai",
            model="test-model",
            prompt_version="v1",
            is_demo=False,
        )
        with (
            patch(
                "bot.services.recovery.claim_recoverable_paid_orders",
                new=AsyncMock(return_value=[make_recoverable()]),
            ),
            patch(
                "bot.services.recovery.process_paid_order",
                new=AsyncMock(return_value=result),
            ),
            patch(
                "bot.services.recovery.notify_admin",
                new=AsyncMock(),
            ),
        ):
            completed = await recover_paid_orders(bot)

        self.assertEqual(completed, 1)
        bot.send_message.assert_awaited_once()
        self.assertIn("Готовый результат", bot.send_message.await_args.args[1])

    async def test_failed_recovery_marks_order_failed(self) -> None:
        bot = AsyncMock()
        fail_order = AsyncMock()
        with (
            patch(
                "bot.services.recovery.claim_recoverable_paid_orders",
                new=AsyncMock(return_value=[make_recoverable()]),
            ),
            patch(
                "bot.services.recovery.process_paid_order",
                new=AsyncMock(side_effect=RuntimeError("AI unavailable")),
            ),
            patch("bot.services.recovery.fail_order", new=fail_order),
            patch(
                "bot.services.recovery.notify_admin",
                new=AsyncMock(),
            ),
        ):
            completed = await recover_paid_orders(bot)

        self.assertEqual(completed, 0)
        fail_order.assert_awaited_once_with(7, "RuntimeError")
        bot.send_message.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
