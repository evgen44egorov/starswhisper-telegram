import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date, time
from html import escape
from typing import TypeVar

from bot.config import get_settings
from bot.database.models import Order, Profile
from bot.database.repositories import complete_order, get_profile
from bot.services.ai import AIResult, AstrobotAIService
from bot.services.orders import parse_order_input, service_label
from bot.utils.telegram import escape_and_limit


class OrderProcessingError(RuntimeError):
    pass


logger = logging.getLogger(__name__)
T = TypeVar("T")


def format_paid_result(order: Order, result_text: str) -> str:
    return (
        f"{escape_and_limit(result_text)}\n\n"
        f"<i>{service_label(order.service_code)} · заказ {escape(order.public_id)}</i>"
    )


async def run_with_one_retry(
    operation: Callable[[], Awaitable[T]],
    delay_seconds: float = 1.0,
) -> T:
    try:
        return await operation()
    except Exception:
        logger.warning("Первая попытка AI-генерации завершилась ошибкой", exc_info=True)
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        return await operation()


async def process_paid_order(order: Order, telegram_id: int) -> AIResult:
    data = parse_order_input(order)
    profile = _profile_from_snapshot(data.get("profile"))
    if profile is None:
        profile = await get_profile(telegram_id)
    if profile is None:
        raise OrderProcessingError("Профиль пользователя не найден")

    service = AstrobotAIService(get_settings())

    if order.service_code == "personal_question":
        result = await run_with_one_retry(
            lambda: service.generate_personal_question(
                profile=profile,
                question_area=str(data["area"]),
                question_text=str(data["question"]),
                current_date=date.today(),
            )
        )
    elif order.service_code == "compatibility":
        result = await run_with_one_retry(
            lambda: service.generate_compatibility(
                profile=profile,
                relationship_type=str(data["relationship_type"]),
                partner_name=str(data["partner_name"]),
                partner_birth_date=date.fromisoformat(
                    str(data["partner_birth_date"])
                ),
                partner_birth_time=(
                    str(data["partner_birth_time"])
                    if data.get("partner_birth_time")
                    else None
                ),
                partner_birth_place=(
                    str(data["partner_birth_place"])
                    if data.get("partner_birth_place")
                    else None
                ),
                current_date=date.today(),
            )
        )
    elif order.service_code == "monthly_forecast":
        result = await run_with_one_retry(
            lambda: service.generate_monthly_forecast(
                profile=profile,
                period=str(data["period_label"]),
                area=str(data["area"]),
                current_date=date.today(),
            )
        )
    elif order.service_code == "natal_chart":
        result = await run_with_one_retry(
            lambda: service.generate_natal_chart(
                profile=profile,
                focus=str(data.get("focus", "Полная карта")),
                subfocus=str(data.get("subfocus", "Баланс всех сфер")),
                life_stage=str(data.get("life_stage", "Стабильный период")),
                time_accuracy=str(data.get("time_accuracy", "Время неизвестно")),
                time_period=(str(data["time_period"]) if data.get("time_period") else None),
                current_date=date.today(),
            )
        )
    elif order.service_code == "tarot_astrology":
        cards = [
            {
                "position": str(card.get("position", "")),
                "card": str(card.get("card", "")),
                "orientation": str(card.get("orientation", "")),
            }
            for card in data.get("cards", [])
            if isinstance(card, dict)
        ]
        if len(cards) != 3:
            raise OrderProcessingError("В заказе отсутствуют карты расклада")
        result = await run_with_one_retry(
            lambda: service.generate_tarot_reading(
                profile=profile,
                spread=str(data["spread"]),
                area=str(data["area"]),
                question=str(data["question"]),
                cards=cards,
                current_date=date.today(),
            )
        )
    else:
        raise OrderProcessingError("Неизвестная услуга заказа")

    await complete_order(
        order_id=order.id,
        result_text=result.text,
        provider=result.provider,
        model=result.model,
        completion_status="completed",
    )
    return result


def _profile_from_snapshot(value: object) -> Profile | None:
    if not isinstance(value, dict):
        return None
    try:
        birth_time_value = value.get("birth_time")
        return Profile(
            name=str(value["name"]),
            birth_date=date.fromisoformat(str(value["birth_date"])),
            birth_time=(
                time.fromisoformat(str(birth_time_value))
                if birth_time_value
                else None
            ),
            birth_place=(
                str(value["birth_place"]) if value.get("birth_place") else None
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
