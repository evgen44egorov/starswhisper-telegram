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


@dataclass(frozen=True)
class AdminCountItem:
    key: str
    count: int


@dataclass(frozen=True)
class AdminStatsRecord:
    users_total: int
    users_today: int
    profiles_total: int
    orders_total: int
    orders_today: int
    paid_payments_total: int
    paid_stars_total: int
    refunded_payments_total: int
    refunded_stars_total: int
    failed_orders_total: int
    active_orders_total: int
    service_counts: list[AdminCountItem]
    status_counts: list[AdminCountItem]


def _order_condition(identifier: str):
    normalized = identifier.strip().upper()
    if normalized.isdigit():
        return or_(Order.id == int(normalized), Order.public_id == normalized)
    return Order.public_id == normalized


async def get_admin_stats() -> AdminStatsRecord:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    async with session_scope() as session:
        async def scalar_int(statement) -> int:
            result = await session.execute(statement)
            return int(result.scalar_one() or 0)

        users_total = await scalar_int(select(func.count(User.id)))
        users_today = await scalar_int(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
        profiles_total = await scalar_int(select(func.count(Profile.id)))
        orders_total = await scalar_int(select(func.count(Order.id)))
        orders_today = await scalar_int(
            select(func.count(Order.id)).where(Order.created_at >= today_start)
        )
        paid_payments_total = await scalar_int(
            select(func.count(Payment.id)).where(Payment.status == "paid")
        )
        paid_stars_total = await scalar_int(
            select(func.coalesce(func.sum(Payment.amount_stars), 0)).where(
                Payment.status == "paid"
            )
        )
        refunded_payments_total = await scalar_int(
            select(func.count(Payment.id)).where(Payment.status == "refunded")
        )
        refunded_stars_total = await scalar_int(
            select(func.coalesce(func.sum(Payment.amount_stars), 0)).where(
                Payment.status == "refunded"
            )
        )
        failed_orders_total = await scalar_int(
            select(func.count(Order.id)).where(Order.status == "failed")
        )
        active_orders_total = await scalar_int(
            select(func.count(Order.id)).where(
                Order.status.in_(
                    {
                        "waiting_payment",
                        "paid",
                        "generating",
                        "recovering",
                        "refund_pending",
                    }
                )
            )
        )

        service_result = await session.execute(
            select(Order.service_code, func.count(Order.id))
            .group_by(Order.service_code)
            .order_by(func.count(Order.id).desc())
        )
        service_counts = [
            AdminCountItem(key=str(service_code), count=int(count))
            for service_code, count in service_result.all()
        ]

        status_result = await session.execute(
            select(Order.status, func.count(Order.id))
            .group_by(Order.status)
            .order_by(func.count(Order.id).desc())
        )
        status_counts = [
            AdminCountItem(key=str(status), count=int(count))
            for status, count in status_result.all()
        ]

        return AdminStatsRecord(
            users_total=users_total,
            users_today=users_today,
            profiles_total=profiles_total,
            orders_total=orders_total,
            orders_today=orders_today,
            paid_payments_total=paid_payments_total,
            paid_stars_total=paid_stars_total,
            refunded_payments_total=refunded_payments_total,
            refunded_stars_total=refunded_stars_total,
            failed_orders_total=failed_orders_total,
            active_orders_total=active_orders_total,
            service_counts=service_counts,
            status_counts=status_counts,
        )


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
