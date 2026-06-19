from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select

from bot.database.models import Order, Payment, Profile, User
from bot.database.session import session_scope


@dataclass(frozen=True)
class AdminOrderRecord:
    order: Order
    user: User
    payment: Payment | None


@dataclass(frozen=True)
class AdminUserRecord:
    user: User
    profile: Profile | None
    orders_count: int


def _order_condition(identifier: str):
    normalized = identifier.strip().upper()
    if normalized.isdigit():
        return or_(Order.id == int(normalized), Order.public_id == normalized)
    return Order.public_id == normalized


async def list_admin_orders(limit: int = 10) -> list[AdminOrderRecord]:
    async with session_scope() as session:
        result = await session.execute(
            select(Order, User, Payment)
            .join(User, Order.user_id == User.id)
            .outerjoin(Payment, Payment.order_id == Order.id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return [AdminOrderRecord(*row) for row in result.all()]


async def get_admin_order(identifier: str) -> AdminOrderRecord | None:
    async with session_scope() as session:
        result = await session.execute(
            select(Order, User, Payment)
            .join(User, Order.user_id == User.id)
            .outerjoin(Payment, Payment.order_id == Order.id)
            .where(_order_condition(identifier))
        )
        row = result.one_or_none()
        return AdminOrderRecord(*row) if row else None


async def get_admin_user(telegram_id: int) -> AdminUserRecord | None:
    async with session_scope() as session:
        result = await session.execute(
            select(User, Profile, func.count(Order.id))
            .outerjoin(Profile, Profile.user_id == User.id)
            .outerjoin(Order, Order.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .group_by(User.id, Profile.id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return AdminUserRecord(user=row[0], profile=row[1], orders_count=row[2])


async def claim_order_retry(identifier: str) -> AdminOrderRecord | None:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Order, User, Payment)
                .join(User, Order.user_id == User.id)
                .join(Payment, Payment.order_id == Order.id)
                .where(
                    _order_condition(identifier),
                    Order.status == "failed",
                    Payment.status == "paid",
                )
            )
            row = result.one_or_none()
            if row is None:
                return None
            order, user, payment = row
            order.status = "generating"
            order.error_message = None
            order.generation_started_at = datetime.now()
            return AdminOrderRecord(order, user, payment)


async def claim_order_refund(identifier: str) -> AdminOrderRecord | None:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Order, User, Payment)
                .join(User, Order.user_id == User.id)
                .join(Payment, Payment.order_id == Order.id)
                .where(
                    _order_condition(identifier),
                    Payment.status == "paid",
                    Payment.telegram_payment_charge_id.is_not(None),
                )
            )
            row = result.one_or_none()
            if row is None:
                return None
            order, user, payment = row
            payment.status = "refund_pending"
            return AdminOrderRecord(order, user, payment)


async def finish_order_refund(order_id: int, succeeded: bool) -> None:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Order, Payment)
                .join(Payment, Payment.order_id == Order.id)
                .where(Order.id == order_id, Payment.status == "refund_pending")
            )
            row = result.one_or_none()
            if row is None:
                return
            order, payment = row
            if succeeded:
                payment.status = "refunded"
                payment.refunded_at = datetime.now()
                order.status = "refunded"
            else:
                payment.status = "paid"
