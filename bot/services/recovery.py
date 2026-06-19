import logging
from html import escape

from aiogram import Bot

from bot.database.repositories import (
    claim_recoverable_paid_orders,
    fail_order,
)
from bot.keyboards.main_menu import main_menu_keyboard
from bot.services.admin import notify_admin
from bot.services.order_processor import format_paid_result, process_paid_order
from bot.texts.ru import PAYMENT_GENERATION_FAILED_TEXT

logger = logging.getLogger(__name__)


async def recover_paid_orders(bot: Bot) -> int:
    recoverable = await claim_recoverable_paid_orders()
    if not recoverable:
        return 0

    await notify_admin(
        bot,
        f"🔄 <b>Восстановление заказов</b>\n\nНайдено: {len(recoverable)}",
    )
    completed = 0
    for item in recoverable:
        order = item.order
        try:
            result = await process_paid_order(order, item.telegram_id)
        except Exception as error:
            logger.exception("Не удалось восстановить заказ %s", order.id)
            await fail_order(order.id, type(error).__name__)
            await notify_admin(
                bot,
                "⚠️ <b>Ошибка восстановления заказа</b>\n\n"
                f"Заказ: <code>{escape(order.public_id)}</code>\n"
                f"Telegram ID: <code>{item.telegram_id}</code>\n"
                f"Ошибка: {escape(type(error).__name__)}",
            )
            try:
                await bot.send_message(
                    item.telegram_id,
                    PAYMENT_GENERATION_FAILED_TEXT.format(
                        public_id=escape(order.public_id)
                    ),
                    reply_markup=main_menu_keyboard(),
                )
            except Exception:
                logger.exception(
                    "Не удалось уведомить пользователя об ошибке заказа %s",
                    order.id,
                )
            continue

        completed += 1
        try:
            await bot.send_message(
                item.telegram_id,
                format_paid_result(order, result.text),
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            logger.exception(
                "Заказ %s восстановлен, но результат не отправлен пользователю",
                order.id,
            )
            await notify_admin(
                bot,
                "⚠️ <b>Результат восстановлен, но не доставлен</b>\n\n"
                f"Заказ: <code>{escape(order.public_id)}</code>\n"
                f"Telegram ID: <code>{item.telegram_id}</code>",
            )

    logger.info(
        "Восстановление оплаченных заказов завершено: %s из %s",
        completed,
        len(recoverable),
    )
    return completed
