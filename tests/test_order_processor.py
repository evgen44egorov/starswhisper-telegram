import unittest
from unittest.mock import AsyncMock

from bot.services.order_processor import run_with_one_retry


class OrderProcessorRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_once_after_temporary_error(self) -> None:
        operation = AsyncMock(side_effect=[RuntimeError("temporary"), "ready"])

        result = await run_with_one_retry(operation, delay_seconds=0)

        self.assertEqual(result, "ready")
        self.assertEqual(operation.await_count, 2)

    async def test_second_error_is_propagated(self) -> None:
        operation = AsyncMock(
            side_effect=[RuntimeError("first"), RuntimeError("second")]
        )

        with self.assertRaisesRegex(RuntimeError, "second"):
            await run_with_one_retry(operation, delay_seconds=0)

        self.assertEqual(operation.await_count, 2)


if __name__ == "__main__":
    unittest.main()
