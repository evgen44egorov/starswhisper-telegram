import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from aiogram.types import User as TelegramUser

from bot.config import Settings
from bot.database.admin import (
    claim_order_refund,
    claim_order_retry,
    finish_order_refund,
    get_admin_order,
    get_admin_user,
    list_admin_orders,
)
from bot.database.repositories import (
    create_pending_order_and_payment,
    fail_order,
    record_successful_payment,
    save_profile,
)
from bot.database.session import close_database, configure_database, init_database
from bot.services.admin import format_admin_order, is_admin


def make_settings(admin_id: int | None) -> Settings:
    return Settings(
        BOT_TOKEN="test-token-longer-than-20-characters",
        ADMIN_TELEGRAM_ID=admin_id,
        _env_file=None,
    )


class AdminAccessTests(unittest.TestCase):
    def test_only_configured_telegram_id_is_admin(self) -> None:
        with patch("bot.services.admin.get_settings", return_value=make_settings(42)):
            self.assertTrue(is_admin(42))
            self.assertFalse(is_admin(41))
            self.assertFalse(is_admin(None))


class AdminRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "admin-test.db"
        configure_database(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        await init_database()
        self.telegram_id = 123456
        await save_profile(
            telegram_user=TelegramUser(
                id=self.telegram_id,
                is_bot=False,
                first_name="Анна",
                username="anna_test",
            ),
            name="Анна",
            birth_date=date(1996, 8, 14),
            birth_time=None,
            birth_place=None,
        )

    async def asyncTearDown(self) -> None:
        await close_database()
        self.temp_dir.cleanup()

    async def create_paid_order(self, charge_id: str):
        order, payment = await create_pending_order_and_payment(
            telegram_id=self.telegram_id,
            service_code="personal_question",
            price_stars=1,
            input_data={"area": "Работа", "question": "Что дальше?"},
            public_id_prefix="Q",
        )
        paid_order, _, error = await record_successful_payment(
            telegram_id=self.telegram_id,
            invoice_payload=payment.invoice_payload,
            currency="XTR",
            total_amount=1,
            telegram_charge_id=charge_id,
            provider_charge_id="",
        )
        self.assertIsNone(error)
        self.assertIsNotNone(paid_order)
        return order

    async def test_lists_and_formats_orders_and_users(self) -> None:
        order = await self.create_paid_order("charge-list")
        records = await list_admin_orders()
        self.assertEqual(len(records), 1)
        self.assertIn(order.public_id, format_admin_order(records[0]))

        by_public_id = await get_admin_order(order.public_id.lower())
        by_internal_id = await get_admin_order(str(order.id))
        self.assertIsNotNone(by_public_id)
        self.assertIsNotNone(by_internal_id)

        user = await get_admin_user(self.telegram_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.orders_count, 1)

    async def test_retry_claim_is_available_once_for_failed_paid_order(self) -> None:
        order = await self.create_paid_order("charge-retry")
        await fail_order(order.id, "TimeoutError")

        claimed = await claim_order_retry(order.public_id)
        duplicate = await claim_order_retry(order.public_id)
        self.assertIsNotNone(claimed)
        self.assertIsNone(duplicate)
        self.assertEqual(claimed.order.status, "generating")

    async def test_refund_claim_is_idempotent_and_can_recover(self) -> None:
        order = await self.create_paid_order("charge-refund")

        first = await claim_order_refund(order.public_id)
        duplicate = await claim_order_refund(order.public_id)
        self.assertIsNotNone(first)
        self.assertIsNone(duplicate)

        await finish_order_refund(order.id, succeeded=False)
        retry = await claim_order_refund(order.public_id)
        self.assertIsNotNone(retry)

        await finish_order_refund(order.id, succeeded=True)
        record = await get_admin_order(order.public_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.order.status, "refunded")
        self.assertEqual(record.payment.status, "refunded")
        self.assertIsNone(await claim_order_refund(order.public_id))


if __name__ == "__main__":
    unittest.main()
