import logging
from html import escape

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.admin import (
    claim_order_refund,
    claim_order_retry,
    finish_order_refund,
    get_admin_order,
    get_admin_user,
    list_admin_orders,
)
from bot.database.repositories import fail_order
from bot.keyboards.main_menu import main_menu_keyboard
from bot.services.admin import format_admin_order, format_admin_user, is_admin
from bot.services.order_processor import process_paid_order
from bot.services.orders import service_label, status_label
from bot.services.results import send_order_result

logger = logging.getLogger(__name__)
router = Router(name="admin")
ADMIN_COMMANDS = (
    "admin",
    "admin_orders",
    "admin_order",
    "admin_user",
    "admin_retry",
    "admin_refund",
)


def _argument(message: Message) -> str | None:
    parts = (message.text or "").strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None


def _admin_help() -> str:
    return (
        "🛠 <b>Админ-команды</b>\n\n"
        "/admin_orders — последние заказы\n"
        "/admin_order &lt;ID&gt; — карточка заказа\n"
        "/admin_user &lt;Telegram ID&gt; — пользователь\n"
        "/admin_retry &lt;ID&gt; — повторить неудачную генерацию\n"
        "/admin_refund &lt;ID&gt; — вернуть Stars\n\n"
        "Для заказа можно использовать публичный или внутренний ID."
    )


@router.message(Command(*ADMIN_COMMANDS))
async def admin_commands(message: Message, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Эта команда недоступна.")
        return

    command = (message.text or "").split(maxsplit=1)[0].split("@", 1)[0]
    argument = _argument(message)

    if command == "/admin":
        await message.answer(_admin_help())
        return

    if command == "/admin_orders":
        records = await list_admin_orders()
        if not records:
            await message.answer("Заказов пока нет.")
            return
        lines = ["📚 <b>Последние заказы</b>"]
        for record in records:
            order = record.order
            lines.append(
                f"<code>{escape(order.public_id)}</code> · "
                f"{service_label(order.service_code)} · {status_label(order.status)} · "
                f"{order.price_stars} ⭐"
            )
        await message.answer("\n".join(lines))
        return

    if command == "/admin_user":
        if argument is None or not argument.isdigit():
            await message.answer("Формат: /admin_user &lt;Telegram ID&gt;")
            return
        record = await get_admin_user(int(argument))
        await message.answer(
            format_admin_user(record) if record else "Пользователь не найден."
        )
        return

    if argument is None:
        await message.answer(f"Укажи ID заказа после команды {escape(command)}.")
        return

    if command == "/admin_order":
        record = await get_admin_order(argument)
        await message.answer(format_admin_order(record) if record else "Заказ не найден.")
        return

    if command == "/admin_retry":
        record = await claim_order_retry(argument)
        if record is None:
            await message.answer(
                "Повтор недоступен: нужен оплаченный заказ со статусом ошибки."
            )
            return
        try:
            result = await process_paid_order(record.order, record.user.telegram_id)
            await send_order_result(
                bot=bot,
                chat_id=record.user.telegram_id,
                order=record.order,
                result_text=result.text,
                reply_markup=main_menu_keyboard(),
                is_demo=result.is_demo,
            )
            await message.answer(f"✅ Заказ {escape(record.order.public_id)} обработан.")
        except Exception as error:
            logger.exception("Ошибка повторной генерации заказа %s", record.order.id)
            await fail_order(record.order.id, type(error).__name__)
            await message.answer("⚠️ Повторная генерация завершилась ошибкой.")
        return

    if command == "/admin_refund":
        record = await claim_order_refund(argument)
        if record is None or record.payment is None:
            await message.answer("Возврат недоступен: оплаченный платёж не найден.")
            return
        charge_id = record.payment.telegram_payment_charge_id
        if not charge_id:
            await finish_order_refund(record.order.id, succeeded=False)
            await message.answer("Возврат недоступен: у платежа нет charge ID.")
            return
        try:
            await bot.refund_star_payment(
                user_id=record.user.telegram_id,
                telegram_payment_charge_id=charge_id,
            )
        except Exception:
            logger.exception("Ошибка возврата Stars для заказа %s", record.order.id)
            await finish_order_refund(record.order.id, succeeded=False)
            await message.answer("⚠️ Telegram не выполнил возврат. Статус платежа восстановлен.")
            return
        await finish_order_refund(record.order.id, succeeded=True)
        await message.answer(
            f"↩️ Возврат по заказу {escape(record.order.public_id)} выполнен."
        )
