import json
import secrets
from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import uuid4

from aiogram.types import User as TelegramUser
from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from bot.database.models import AIGeneration, Order, Payment, Profile, User
from bot.database.session import session_scope


@dataclass(frozen=True)
class RecoverableOrder:
    order: Order
    telegram_id: int


async def get_profile(telegram_id: int) -> Profile | None:
    async with session_scope() as session:
        result = await session.execute(
            select(Profile).join(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def save_profile(
    telegram_user: TelegramUser,
    name: str,
    birth_date: date,
    birth_time: time | None,
    birth_place: str | None,
) -> Profile:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_user.id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(telegram_id=telegram_user.id)
                session.add(user)
                await session.flush()

            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.language_code = telegram_user.language_code

            result = await session.execute(
                select(Profile).where(Profile.user_id == user.id)
            )
            profile = result.scalar_one_or_none()

            if profile is None:
                profile = Profile(user_id=user.id, name=name, birth_date=birth_date)
                session.add(profile)

            profile.name = name
            profile.birth_date = birth_date
            profile.birth_time = birth_time
            profile.birth_place = birth_place

            await session.execute(
                sql_delete(AIGeneration).where(
                    AIGeneration.user_id == user.id,
                    AIGeneration.service_code == "daily_forecast",
                )
            )

        return profile


async def delete_profile(telegram_id: int) -> bool:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Profile).join(User).where(User.telegram_id == telegram_id)
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                return False

            await session.execute(
                sql_delete(AIGeneration).where(AIGeneration.user_id == profile.user_id)
            )
            await session.delete(profile)
            return True


async def get_cached_daily_forecast(
    telegram_id: int,
    generation_date: date,
) -> AIGeneration | None:
    async with session_scope() as session:
        result = await session.execute(
            select(AIGeneration)
            .join(User)
            .where(
                User.telegram_id == telegram_id,
                AIGeneration.service_code == "daily_forecast",
                AIGeneration.generation_date == generation_date,
            )
        )
        return result.scalar_one_or_none()


async def save_daily_forecast(
    telegram_id: int,
    generation_date: date,
    result_text: str,
    provider: str,
    model: str,
    prompt_version: str,
    is_demo: bool,
) -> AIGeneration:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError("Пользователь не найден")

            result = await session.execute(
                select(AIGeneration).where(
                    AIGeneration.user_id == user.id,
                    AIGeneration.service_code == "daily_forecast",
                    AIGeneration.generation_date == generation_date,
                )
            )
            generation = result.scalar_one_or_none()
            if generation is None:
                generation = AIGeneration(
                    user_id=user.id,
                    service_code="daily_forecast",
                    generation_date=generation_date,
                    prompt_version=prompt_version,
                    provider=provider,
                    model=model,
                    result_text=result_text,
                    is_demo=is_demo,
                )
                session.add(generation)
            else:
                generation.prompt_version = prompt_version
                generation.provider = provider
                generation.model = model
                generation.result_text = result_text
                generation.is_demo = is_demo

        return generation


async def create_test_order(
    telegram_id: int,
    service_code: str,
    price_stars: int,
    input_data: dict[str, object],
    public_id_prefix: str,
) -> Order:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError("Пользователь не найден")

            order = Order(
                public_id=f"{public_id_prefix}-{uuid4().hex[:10].upper()}",
                user_id=user.id,
                service_code=service_code,
                status="test_generating",
                price_stars=price_stars,
                currency="XTR",
                input_data_json=json.dumps(input_data, ensure_ascii=False),
                generation_started_at=datetime.now(),
            )
            session.add(order)

        return order


async def complete_order(
    order_id: int,
    result_text: str,
    provider: str,
    model: str,
    completion_status: str = "test_completed",
) -> None:
    async with session_scope() as session:
        async with session.begin():
            order = await session.get(Order, order_id)
            if order is None:
                raise RuntimeError("Заказ не найден")

            order.status = completion_status
            order.result_text = result_text
            order.provider = provider
            order.model = model
            order.delivered_at = datetime.now()


async def fail_order(order_id: int, error_message: str) -> None:
    async with session_scope() as session:
        async with session.begin():
            order = await session.get(Order, order_id)
            if order is None:
                return

            order.status = "failed"
            order.error_message = error_message[:500]


async def create_question_order(
    telegram_id: int,
    question_area: str,
    question_text: str,
) -> Order:
    return await create_test_order(
        telegram_id=telegram_id,
        service_code="personal_question",
        price_stars=350,
        input_data={"area": question_area, "question": question_text},
        public_id_prefix="Q",
    )


async def complete_question_order(
    order_id: int,
    result_text: str,
    provider: str,
    model: str,
) -> None:
    await complete_order(order_id, result_text, provider, model)


async def fail_question_order(order_id: int, error_message: str) -> None:
    await fail_order(order_id, error_message)


async def list_user_orders(telegram_id: int, limit: int = 10) -> list[Order]:
    async with session_scope() as session:
        result = await session.execute(
            select(Order)
            .join(User)
            .where(
                User.telegram_id == telegram_id,
                Order.status != "data_deleted",
            )
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_user_order(telegram_id: int, order_id: int) -> Order | None:
    async with session_scope() as session:
        result = await session.execute(
            select(Order)
            .join(User)
            .where(
                User.telegram_id == telegram_id,
                Order.id == order_id,
                Order.status != "data_deleted",
            )
        )
        return result.scalar_one_or_none()


async def get_user_order_payment(
    telegram_id: int,
    order_id: int,
) -> Payment | None:
    async with session_scope() as session:
        result = await session.execute(
            select(Payment)
            .join(Order, Payment.order_id == Order.id)
            .join(User, Payment.user_id == User.id)
            .where(
                User.telegram_id == telegram_id,
                Order.id == order_id,
                Order.status == "waiting_payment",
                Payment.status.in_({"waiting_payment", "pre_checkout_approved"}),
            )
        )
        return result.scalar_one_or_none()


async def delete_user_order(telegram_id: int, order_id: int) -> bool:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Order)
                .join(User)
                .where(
                    User.telegram_id == telegram_id,
                    Order.id == order_id,
                )
            )
            order = result.scalar_one_or_none()
            if order is None:
                return False

            if order.status in {"waiting_payment", "paid", "generating"}:
                return False

            payment_result = await session.execute(
                select(Payment).where(Payment.order_id == order.id)
            )
            payment = payment_result.scalar_one_or_none()
            if payment is not None and payment.status in {"paid", "refunded"}:
                order.input_data_json = "{}"
                order.result_text = None
                order.error_message = None
                order.status = "data_deleted"
                return True

            if payment is not None:
                await session.delete(payment)

            await session.delete(order)
            return True


async def create_pending_order_and_payment(
    telegram_id: int,
    service_code: str,
    price_stars: int,
    input_data: dict[str, object],
    public_id_prefix: str,
) -> tuple[Order, Payment]:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError("Пользователь не найден")

            order = Order(
                public_id=f"{public_id_prefix}-{uuid4().hex[:10].upper()}",
                user_id=user.id,
                service_code=service_code,
                status="waiting_payment",
                price_stars=price_stars,
                currency="XTR",
                input_data_json=json.dumps(input_data, ensure_ascii=False),
            )
            session.add(order)
            await session.flush()

            payment = Payment(
                order_id=order.id,
                user_id=user.id,
                invoice_payload=f"astro_{secrets.token_urlsafe(24)}",
                currency="XTR",
                amount_stars=price_stars,
                status="waiting_payment",
            )
            session.add(payment)

        return order, payment


async def approve_pre_checkout(
    telegram_id: int,
    invoice_payload: str,
    currency: str,
    total_amount: int,
) -> tuple[bool, str | None]:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Payment, Order)
                .join(Order, Payment.order_id == Order.id)
                .join(User, Payment.user_id == User.id)
                .where(
                    User.telegram_id == telegram_id,
                    Payment.invoice_payload == invoice_payload,
                )
            )
            row = result.one_or_none()
            if row is None:
                return False, "Заказ не найден. Вернись в бот и создай его заново."

            payment, order = row
            if payment.status not in {"waiting_payment", "pre_checkout_approved"}:
                return False, "Этот счёт уже обработан или больше не активен."
            if order.status != "waiting_payment":
                return False, "Заказ больше не ожидает оплату."
            if currency != "XTR" or payment.currency != "XTR":
                return False, "Неверная валюта платежа."
            if total_amount != payment.amount_stars or total_amount != order.price_stars:
                return False, "Сумма счёта изменилась. Создай заказ заново."

            payment.status = "pre_checkout_approved"
            return True, None


async def record_successful_payment(
    telegram_id: int,
    invoice_payload: str,
    currency: str,
    total_amount: int,
    telegram_charge_id: str,
    provider_charge_id: str | None,
) -> tuple[Order | None, bool, str | None]:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Payment, Order)
                .join(Order, Payment.order_id == Order.id)
                .join(User, Payment.user_id == User.id)
                .where(
                    User.telegram_id == telegram_id,
                    Payment.invoice_payload == invoice_payload,
                )
            )
            row = result.one_or_none()
            if row is None:
                return None, False, "Оплаченный заказ не найден. Обратись в поддержку."

            payment, order = row
            if (
                currency != "XTR"
                or currency != payment.currency
                or total_amount != payment.amount_stars
                or total_amount != order.price_stars
            ):
                return None, False, "Данные оплаты не совпали с заказом."

            if payment.status == "paid":
                if payment.telegram_payment_charge_id == telegram_charge_id:
                    return order, False, None
                return None, False, "Платёж уже был обработан с другим идентификатором."

            if payment.status not in {"waiting_payment", "pre_checkout_approved"}:
                return None, False, "Платёж находится в неподходящем статусе."

            payment.status = "paid"
            payment.telegram_payment_charge_id = telegram_charge_id
            payment.provider_payment_charge_id = provider_charge_id
            payment.paid_at = datetime.now()
            order.status = "paid"
            return order, True, None


async def claim_paid_order_for_generation(
    telegram_id: int,
    order_id: int,
) -> bool:
    async with session_scope() as session:
        async with session.begin():
            result = await session.execute(
                select(Order)
                .join(User)
                .where(
                    User.telegram_id == telegram_id,
                    Order.id == order_id,
                )
            )
            order = result.scalar_one_or_none()
            if order is None or order.status != "paid":
                return False

            order.status = "generating"
            order.generation_started_at = datetime.now()
            return True


async def claim_recoverable_paid_orders() -> list[RecoverableOrder]:
    """Claim unfinished paid orders after a process restart.

    Long polling supports a single bot process. Any ``recovering`` rows therefore
    belong to an earlier process that stopped before finishing and can be reset.
    """
    async with session_scope() as session:
        async with session.begin():
            recovering_result = await session.execute(
                select(Order).where(Order.status == "recovering")
            )
            for interrupted_order in recovering_result.scalars():
                interrupted_order.status = "generating"

            result = await session.execute(
                select(Order, User.telegram_id)
                .join(User, Order.user_id == User.id)
                .join(Payment, Payment.order_id == Order.id)
                .where(
                    Order.status.in_({"paid", "generating"}),
                    Payment.status == "paid",
                )
                .order_by(Order.created_at.asc())
            )
            claimed: list[RecoverableOrder] = []
            for order, telegram_id in result.all():
                order.status = "recovering"
                order.generation_started_at = datetime.now()
                claimed.append(
                    RecoverableOrder(order=order, telegram_id=telegram_id)
                )
            return claimed


async def fail_invoice_creation(order_id: int) -> None:
    async with session_scope() as session:
        async with session.begin():
            order = await session.get(Order, order_id)
            if order is None:
                return
            payment_result = await session.execute(
                select(Payment).where(Payment.order_id == order_id)
            )
            payment = payment_result.scalar_one_or_none()
            order.status = "failed"
            order.error_message = "Не удалось создать счёт"
            if payment is not None:
                payment.status = "invoice_failed"
