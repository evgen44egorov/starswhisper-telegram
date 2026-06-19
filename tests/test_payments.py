import tempfile
import unittest
from datetime import date
from pathlib import Path

from aiogram.types import User as TelegramUser

from bot.config import Settings
from bot.database.repositories import (
    approve_pre_checkout,
    claim_paid_order_for_generation,
    claim_recoverable_paid_orders,
    create_pending_order_and_payment,
    record_successful_payment,
    save_profile,
)
from bot.database.session import close_database, configure_database, init_database
from bot.services.payments import (
    PaymentServiceError,
    effective_price,
    payment_note,
    public_price_label,
    validate_payments_configuration,
)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "BOT_TOKEN": "test-token-longer-than-20-characters",
        "AI_PROVIDER": "openai",
        "AI_API_KEY": "test-api-key",
        "PAYMENTS_MODE": "demo",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


class PaymentSettingsTests(unittest.TestCase):
    def test_demo_and_stars_test_prices(self) -> None:
        demo = make_settings(PAYMENTS_MODE="demo")
        stars_test = make_settings(PAYMENTS_MODE="stars_test")
        self.assertEqual(effective_price("personal_question", demo), 350)
        self.assertEqual(effective_price("personal_question", stars_test), 1)
        self.assertEqual(effective_price("natal_chart", demo), 900)
        self.assertEqual(effective_price("natal_chart", stars_test), 1)
        self.assertEqual(effective_price("tarot_astrology", demo), 300)
        self.assertEqual(effective_price("tarot_astrology", stars_test), 1)
        self.assertEqual(effective_price("numerology", demo), 250)
        self.assertEqual(effective_price("numerology", stars_test), 1)
        self.assertIn("доступна бесплатно", payment_note("personal_question", demo))
        self.assertIn("реальное списание одной звезды", payment_note("personal_question", stars_test))
        self.assertEqual(
            public_price_label("personal_question", demo),
            "цена 350 Stars · сейчас бесплатно",
        )
        self.assertEqual(
            public_price_label("personal_question", stars_test),
            "цена 350 Stars · сейчас 1 Star",
        )

    def test_live_mode_requires_support(self) -> None:
        settings = make_settings(
            PAYMENTS_MODE="stars",
            ADMIN_TELEGRAM_ID=123456,
            SUPPORT_USERNAME="",
        )
        with self.assertRaises(PaymentServiceError):
            validate_payments_configuration(settings)

    def test_live_mode_requires_admin(self) -> None:
        settings = make_settings(
            PAYMENTS_MODE="stars",
            ADMIN_TELEGRAM_ID=None,
            SUPPORT_USERNAME="astrobot_support",
        )
        with self.assertRaises(PaymentServiceError):
            validate_payments_configuration(settings)

    def test_live_mode_accepts_complete_configuration(self) -> None:
        settings = make_settings(
            PAYMENTS_MODE="stars",
            ADMIN_TELEGRAM_ID=123456,
            SUPPORT_USERNAME="astrobot_support",
        )
        validate_payments_configuration(settings)


class PaymentRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "payments-test.db"
        configure_database(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        await init_database()

        self.telegram_user = TelegramUser(
            id=123456,
            is_bot=False,
            first_name="Анна",
        )
        await save_profile(
            telegram_user=self.telegram_user,
            name="Анна",
            birth_date=date(1996, 8, 14),
            birth_time=None,
            birth_place=None,
        )

    async def asyncTearDown(self) -> None:
        await close_database()
        self.temp_dir.cleanup()

    async def test_payment_is_verified_and_processed_once(self) -> None:
        order, payment = await create_pending_order_and_payment(
            telegram_id=self.telegram_user.id,
            service_code="personal_question",
            price_stars=350,
            input_data={"area": "Работа", "question": "Как обсудить новую роль?"},
            public_id_prefix="Q",
        )

        wrong_ok, _ = await approve_pre_checkout(
            telegram_id=self.telegram_user.id,
            invoice_payload=payment.invoice_payload,
            currency="XTR",
            total_amount=1,
        )
        self.assertFalse(wrong_ok)

        ok, error = await approve_pre_checkout(
            telegram_id=self.telegram_user.id,
            invoice_payload=payment.invoice_payload,
            currency="XTR",
            total_amount=350,
        )
        self.assertTrue(ok)
        self.assertIsNone(error)

        paid_order, should_generate, payment_error = await record_successful_payment(
            telegram_id=self.telegram_user.id,
            invoice_payload=payment.invoice_payload,
            currency="XTR",
            total_amount=350,
            telegram_charge_id="charge-123",
            provider_charge_id="",
        )
        self.assertIsNotNone(paid_order)
        self.assertTrue(should_generate)
        self.assertIsNone(payment_error)

        duplicate_order, duplicate_generate, _ = await record_successful_payment(
            telegram_id=self.telegram_user.id,
            invoice_payload=payment.invoice_payload,
            currency="XTR",
            total_amount=350,
            telegram_charge_id="charge-123",
            provider_charge_id="",
        )
        self.assertIsNotNone(duplicate_order)
        self.assertFalse(duplicate_generate)

        self.assertTrue(
            await claim_paid_order_for_generation(self.telegram_user.id, order.id)
        )
        self.assertFalse(
            await claim_paid_order_for_generation(self.telegram_user.id, order.id)
        )

    async def test_paid_order_is_claimed_for_startup_recovery(self) -> None:
        order, payment = await create_pending_order_and_payment(
            telegram_id=self.telegram_user.id,
            service_code="personal_question",
            price_stars=1,
            input_data={"area": "Работа", "question": "Что дальше?"},
            public_id_prefix="Q",
        )
        await record_successful_payment(
            telegram_id=self.telegram_user.id,
            invoice_payload=payment.invoice_payload,
            currency="XTR",
            total_amount=1,
            telegram_charge_id="charge-recovery",
            provider_charge_id="",
        )

        claimed = await claim_recoverable_paid_orders()

        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].order.id, order.id)
        self.assertEqual(claimed[0].order.status, "recovering")
        self.assertEqual(claimed[0].telegram_id, self.telegram_user.id)


if __name__ == "__main__":
    unittest.main()
