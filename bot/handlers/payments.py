import logging
from html import escape

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

from bot.database.repositories import (
    approve_pre_checkout,
    claim_paid_order_for_generation,
    fail_order,
    record_successful_payment,
)
from bot.keyboards.main_menu import main_menu_keyboard
from bot.services.admin import notify_admin
from bot.services.order_processor import format_paid_result, process_paid_order
from bot.services.results import send_order_result
from bot.services.screens import clear_screen, remember_screen, show_screen
from bot.texts.ru import (
    PAYMENT_ALREADY_PROCESSED_TEXT,
    PAYMENT_ERROR_TEXT,
    PAYMENT_GENERATION_FAILED_TEXT,
    PAYMENT_SUCCESS_TEXT,
)

logger = logging.getLogger(__name__)
router = Router(name="payments")

@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    try:
        ok, error_message = await approve_pre_checkout(
            telegram_id=query.from_user.id,
            invoice_payload=query.invoice_payload,
            currency=query.currency,
            total_amount=query.total_amount,
        )
        if ok:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message=error_message)
    except Exception:
        logger.exception("Ошибка проверки pre-checkout")
        await query.answer(
            ok=False,
            error_message="Не удалось проверить заказ. Попробуй создать счёт заново.",
        )


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    successful_payment = message.successful_payment
    if successful_payment is None or message.from_user is None:
        return

    try:
        order, should_generate, error_message = await record_successful_payment(
            telegram_id=message.from_user.id,
            invoice_payload=successful_payment.invoice_payload,
            currency=successful_payment.currency,
            total_amount=successful_payment.total_amount,
            telegram_charge_id=successful_payment.telegram_payment_charge_id,
            provider_charge_id=successful_payment.provider_payment_charge_id,
        )
    except Exception:
        logger.exception("Ошибка записи успешного платежа")
        await notify_admin(
            message.bot,
            "⚠️ <b>Ошибка записи успешного платежа</b>\n\n"
            f"Telegram ID: <code>{message.from_user.id}</code>",
        )
        await show_screen(
            message,
            PAYMENT_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return
    if order is None or error_message:
        logger.error("Не удалось сопоставить успешный платёж: %s", error_message)
        await notify_admin(
            message.bot,
            "⚠️ <b>Платёж не сопоставлен с заказом</b>\n\n"
            f"Telegram ID: <code>{message.from_user.id}</code>",
        )
        await show_screen(
            message,
            PAYMENT_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    if not should_generate:
        await show_screen(
            message,
            PAYMENT_ALREADY_PROCESSED_TEXT.format(public_id=escape(order.public_id)),
            reply_markup=main_menu_keyboard(),
        )
        return

    await notify_admin(
        message.bot,
        "✅ <b>Успешная оплата</b>\n\n"
        f"Заказ: <code>{escape(order.public_id)}</code>\n"
        f"Telegram ID: <code>{message.from_user.id}</code>\n"
        f"Сумма: {successful_payment.total_amount} Stars",
    )

    claimed = await claim_paid_order_for_generation(message.from_user.id, order.id)
    if not claimed:
        await show_screen(
            message,
            PAYMENT_ALREADY_PROCESSED_TEXT.format(public_id=escape(order.public_id)),
            reply_markup=main_menu_keyboard(),
        )
        return

    progress_message = await show_screen(
        message,
        PAYMENT_SUCCESS_TEXT.format(public_id=escape(order.public_id)),
    )
    try:
        result = await process_paid_order(order, message.from_user.id)
        if order.service_code == "natal_chart":
            await clear_screen(progress_message)
            last_message = await send_order_result(
                bot=progress_message.bot,
                chat_id=progress_message.chat.id,
                order=order,
                result_text=result.text,
                reply_markup=main_menu_keyboard(),
                is_demo=result.is_demo,
            )
            remember_screen(last_message)
        else:
            await show_screen(
                progress_message,
                format_paid_result(order, result.text),
                reply_markup=main_menu_keyboard(),
            )
    except Exception as error:
        logger.exception("Ошибка генерации оплаченного заказа")
        await fail_order(order.id, type(error).__name__)
        await notify_admin(
            message.bot,
            "⚠️ <b>Ошибка AI-генерации</b>\n\n"
            f"Заказ: <code>{escape(order.public_id)}</code>\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Ошибка: {escape(type(error).__name__)}",
        )
        await show_screen(
            progress_message,
            PAYMENT_GENERATION_FAILED_TEXT.format(
                public_id=escape(order.public_id)
            ),
            reply_markup=main_menu_keyboard(),
        )
