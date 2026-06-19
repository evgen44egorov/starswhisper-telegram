from dataclasses import dataclass

from aiogram.types import LabeledPrice, Message

from bot.config import Settings, get_settings
from bot.database.models import Order, Payment, Profile
from bot.database.repositories import (
    create_pending_order_and_payment,
    fail_invoice_creation,
)
from bot.services.admin import notify_admin
from bot.services.screens import clear_screen, remember_screen


class PaymentServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentSpec:
    title: str
    description: str
    price_stars: int
    public_id_prefix: str


PAYMENT_CATALOG = {
    "personal_question": PaymentSpec(
        title="Ответ на личный вопрос",
        description="Персональный символический разбор одного вопроса.",
        price_stars=350,
        public_id_prefix="Q",
    ),
    "compatibility": PaymentSpec(
        title="Совместимость",
        description="Персональный разбор динамики отношений двух людей.",
        price_stars=600,
        public_id_prefix="C",
    ),
    "monthly_forecast": PaymentSpec(
        title="Прогноз на месяц",
        description="Персональный символический прогноз на выбранный месяц.",
        price_stars=400,
        public_id_prefix="M",
    ),
    "natal_chart": PaymentSpec(
        title="Натальная карта",
        description="Глубокий символический астропортрет по данным рождения.",
        price_stars=900,
        public_id_prefix="N",
    ),
    "tarot_astrology": PaymentSpec(
        title="Таро + астрология",
        description="Символический расклад трёх карт с астрологическим контекстом.",
        price_stars=300,
        public_id_prefix="T",
    ),
}


def profile_snapshot(profile: Profile) -> dict[str, object]:
    return {
        "name": profile.name,
        "birth_date": profile.birth_date.isoformat(),
        "birth_time": (
            profile.birth_time.strftime("%H:%M") if profile.birth_time else None
        ),
        "birth_place": profile.birth_place,
    }


def payments_mode(settings: Settings) -> str:
    mode = settings.payments_mode.strip().lower()
    if mode not in {"demo", "stars_test", "stars"}:
        raise PaymentServiceError(f"Неизвестный режим оплаты: {mode}")
    return mode


def stars_enabled(settings: Settings) -> bool:
    return payments_mode(settings) in {"stars_test", "stars"}


def effective_price(service_code: str, settings: Settings) -> int:
    spec = PAYMENT_CATALOG[service_code]
    return 1 if payments_mode(settings) == "stars_test" else spec.price_stars


def payment_note(service_code: str, settings: Settings) -> str:
    mode = payments_mode(settings)
    spec = PAYMENT_CATALOG[service_code]
    if mode == "stars_test":
        return (
            "🧪 Тестовая оплата: 1 Star. Это реальное списание одной звезды. "
            "Условия: /terms"
        )
    if mode == "stars":
        return (
            f"⭐ К оплате: {spec.price_stars} Stars. AI-разбор начнётся после "
            "подтверждения платежа. Условия: /terms"
        )
    return (
        f"⭐ Будущая цена: {spec.price_stars} Stars. "
        "На тестовом запуске оплата не списывается."
    )


def validate_payments_configuration(settings: Settings) -> None:
    mode = payments_mode(settings)
    if mode == "stars":
        if settings.admin_telegram_id is None:
            raise PaymentServiceError(
                "Для PAYMENTS_MODE=stars укажите ADMIN_TELEGRAM_ID в файле .env"
            )
        if not (settings.support_username or "").strip():
            raise PaymentServiceError(
                "Для PAYMENTS_MODE=stars укажите SUPPORT_USERNAME в файле .env"
            )
        api_key = (
            settings.ai_api_key.get_secret_value().strip()
            if settings.ai_api_key
            else ""
        )
        if settings.ai_provider.strip().lower() != "openai" or not api_key:
            raise PaymentServiceError(
                "Для PAYMENTS_MODE=stars настройте AI_PROVIDER=openai и AI_API_KEY"
            )


async def send_stars_invoice(
    source: Message,
    telegram_id: int,
    service_code: str,
    input_data: dict[str, object],
) -> Order:
    settings = get_settings()
    mode = payments_mode(settings)
    if mode not in {"stars_test", "stars"}:
        raise PaymentServiceError("Оплата Stars не включена")

    spec = PAYMENT_CATALOG[service_code]
    price = effective_price(service_code, settings)
    order, payment = await create_pending_order_and_payment(
        telegram_id=telegram_id,
        service_code=service_code,
        price_stars=price,
        input_data=input_data,
        public_id_prefix=spec.public_id_prefix,
    )
    try:
        await send_existing_stars_invoice(source, order, payment)
        await notify_admin(
            source.bot,
            "📝 <b>Новый заказ</b>\n\n"
            f"ID: <code>{order.public_id}</code>\n"
            f"Telegram ID: <code>{telegram_id}</code>\n"
            f"Услуга: {spec.title}\n"
            f"Цена: {price} Stars\n"
            f"Статус: {order.status}",
        )
        return order
    except Exception as error:
        await fail_invoice_creation(order.id)
        raise PaymentServiceError("Не удалось создать счёт Stars") from error


async def send_existing_stars_invoice(
    source: Message,
    order: Order,
    payment: Payment,
) -> None:
    settings = get_settings()
    if not stars_enabled(settings):
        raise PaymentServiceError("Оплата Stars не включена")
    if order.service_code not in PAYMENT_CATALOG:
        raise PaymentServiceError("Услуга не поддерживает оплату Stars")

    spec = PAYMENT_CATALOG[order.service_code]
    is_test_invoice = payment.amount_stars != spec.price_stars
    title = f"ТЕСТ · {spec.title}" if is_test_invoice else spec.title

    try:
        await clear_screen(source)
        invoice_message = await source.bot.send_invoice(
            chat_id=source.chat.id,
            title=title,
            description=spec.description,
            payload=payment.invoice_payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=spec.title, amount=payment.amount_stars)],
        )
        remember_screen(invoice_message)
    except Exception as error:
        raise PaymentServiceError("Не удалось отправить счёт Stars") from error
