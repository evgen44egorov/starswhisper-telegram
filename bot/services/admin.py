import logging
from html import escape

from aiogram import Bot

from bot.config import get_settings
from bot.database.admin import AdminCountItem, AdminOrderRecord, AdminStatsRecord, AdminUserRecord
from bot.services.orders import service_label, status_label

logger = logging.getLogger(__name__)


def is_admin(telegram_id: int | None) -> bool:
    admin_id = get_settings().admin_telegram_id
    return telegram_id is not None and admin_id is not None and telegram_id == admin_id


async def notify_admin(bot: Bot, text: str) -> None:
    admin_id = get_settings().admin_telegram_id
    if admin_id is None:
        return
    try:
        await bot.send_message(admin_id, text)
    except Exception:
        logger.exception("Не удалось отправить уведомление администратору")


def format_admin_order(record: AdminOrderRecord) -> str:
    order, user, payment = record.order, record.user, record.payment
    username = f"@{escape(user.username)}" if user.username else "—"
    payment_status = escape(payment.status) if payment else "нет платежа"
    charge_state = "есть" if payment and payment.telegram_payment_charge_id else "нет"
    error = (
        f"\nОшибка: {escape(order.error_message)}"
        if order.error_message
        else ""
    )
    return (
        f"📝 <b>Заказ {escape(order.public_id)}</b>\n\n"
        f"Внутренний ID: <code>{order.id}</code>\n"
        f"Пользователь: {username}\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Услуга: {service_label(order.service_code)}\n"
        f"Цена: {order.price_stars} Stars\n"
        f"Статус заказа: {status_label(order.status)}\n"
        f"Статус платежа: {payment_status}\n"
        f"Charge ID: {charge_state}\n"
        f"Создан: {order.created_at:%d.%m.%Y %H:%M}"
        f"{error}"
    )


def format_admin_user(record: AdminUserRecord) -> str:
    user, profile = record.user, record.profile
    username = f"@{escape(user.username)}" if user.username else "—"
    profile_name = escape(profile.name) if profile else "не заполнен"
    return (
        "👤 <b>Пользователь</b>\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Username: {username}\n"
        f"Имя профиля: {profile_name}\n"
        f"Заказов: {record.orders_count}\n"
        f"Создан: {user.created_at:%d.%m.%Y %H:%M}"
    )


def _format_count_items(
    items: list[AdminCountItem],
    label_factory,
) -> str:
    if not items:
        return "—"
    return "\n".join(
        f"• {label_factory(item.key)}: <b>{item.count}</b>"
        for item in items
    )


def format_admin_stats(stats: AdminStatsRecord) -> str:
    service_lines = _format_count_items(stats.service_counts, service_label)
    status_lines = _format_count_items(stats.status_counts, status_label)
    return (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователи: <b>{stats.users_total}</b>"
        f" · сегодня +{stats.users_today}\n"
        f"👤 Профили: <b>{stats.profiles_total}</b>\n"
        f"📦 Заказы: <b>{stats.orders_total}</b>"
        f" · сегодня +{stats.orders_today}\n"
        f"⏳ Активные заказы: <b>{stats.active_orders_total}</b>\n"
        f"⚠️ Ошибки: <b>{stats.failed_orders_total}</b>\n\n"
        f"⭐ Оплачено: <b>{stats.paid_stars_total}</b> Stars"
        f" · платежей: {stats.paid_payments_total}\n"
        f"↩️ Возвраты: <b>{stats.refunded_stars_total}</b> Stars"
        f" · платежей: {stats.refunded_payments_total}\n\n"
        f"🔥 <b>Услуги</b>\n{service_lines}\n\n"
        f"📌 <b>Статусы заказов</b>\n{status_lines}"
    )
