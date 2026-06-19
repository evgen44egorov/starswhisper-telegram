import json
from html import escape

from bot.database.models import Order

SERVICE_LABELS = {
    "personal_question": "💌 Личный вопрос",
    "compatibility": "🧩 Совместимость",
    "monthly_forecast": "🌙 Прогноз на месяц",
    "natal_chart": "🪐 Натальная карта",
}

STATUS_LABELS = {
    "test_generating": "⏳ Создаётся",
    "test_completed": "✅ Готов",
    "pending_payment": "⭐ Ожидает оплаты",
    "waiting_payment": "⭐ Ожидает оплаты",
    "paid": "💫 Оплачен",
    "generating": "⏳ Создаётся",
    "recovering": "🔄 Восстанавливается",
    "completed": "✅ Готов",
    "failed": "⚠️ Ошибка",
    "refunded": "↩️ Возвращён",
    "refund_pending": "↩️ Возврат выполняется",
}


def service_label(service_code: str) -> str:
    return SERVICE_LABELS.get(service_code, "🔮 Астрологический разбор")


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, escape(status))


def parse_order_input(order: Order) -> dict[str, object]:
    try:
        value = json.loads(order.input_data_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def format_order_input(order: Order) -> str:
    data = parse_order_input(order)
    if order.service_code == "personal_question":
        return (
            f"Сфера: {escape(str(data.get('area', 'Не указано')))}\n"
            f"Вопрос: {escape(str(data.get('question', 'Не указано')))}"
        )
    if order.service_code == "compatibility":
        return (
            f"Тип отношений: {escape(str(data.get('relationship_type', 'Не указано')))}\n"
            f"Второй человек: {escape(str(data.get('partner_name', 'Не указано')))}\n"
            f"Дата рождения: {escape(str(data.get('partner_birth_date', 'Не указано')))}"
        )
    if order.service_code == "monthly_forecast":
        return (
            f"Период: {escape(str(data.get('period_label', 'Не указано')))}\n"
            f"Фокус: {escape(str(data.get('area', 'Не указано')))}"
        )
    if order.service_code == "natal_chart":
        profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
        return (
            f"Дата рождения: {escape(str(profile.get('birth_date', 'Не указано')))}\n"
            f"Время рождения: {escape(str(profile.get('birth_time') or 'Неизвестно'))}\n"
            f"Место рождения: {escape(str(profile.get('birth_place') or 'Не указано'))}\n"
            f"Точность времени: {escape(str(data.get('time_accuracy', 'Не указано')))}\n"
            f"Жизненный этап: {escape(str(data.get('life_stage', 'Не указано')))}\n"
            f"Фокус: {escape(str(data.get('focus', 'Полная карта')))}\n"
            f"Уточнение: {escape(str(data.get('subfocus', 'Не указано')))}"
        )
    return "Параметры заказа сохранены."


def format_order_card(order: Order) -> str:
    price_label = (
        f"Плановая цена: {order.price_stars} Stars · не списывалась"
        if order.status.startswith("test_")
        else f"Цена: {order.price_stars} Stars"
    )
    created_at = order.created_at.strftime("%d.%m.%Y · %H:%M")
    return (
        f"📦 <b>Заказ {escape(order.public_id)}</b>\n\n"
        f"Услуга: {service_label(order.service_code)}\n"
        f"Статус: {status_label(order.status)}\n"
        f"{price_label}\n"
        f"Создан: {created_at}\n\n"
        f"{format_order_input(order)}"
    )
