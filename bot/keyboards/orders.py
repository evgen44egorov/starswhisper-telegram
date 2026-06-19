from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models import Order
from bot.services.orders import service_label, status_label


def orders_list_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{status_label(order.status)} · {order.public_id} · {service_label(order.service_code)}",
                callback_data=f"orders:view:{order.id}",
            )
        ]
        for order in orders
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="orders:menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_actions_keyboard(order: Order) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if order.status == "waiting_payment":
        rows.append(
            [
                InlineKeyboardButton(
                    text="⭐ Продолжить оплату",
                    callback_data=f"orders:pay:{order.id}",
                )
            ]
        )
    if order.result_text:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📄 Показать результат",
                    callback_data=f"orders:result:{order.id}",
                )
            ]
        )
    if order.status not in {"waiting_payment", "paid", "generating"}:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 Удалить заказ",
                    callback_data=f"orders:delete:{order.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="↩️ К списку",
                callback_data="orders:list",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_result_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ К заказу",
                    callback_data=f"orders:view:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Все заказы",
                    callback_data="orders:list",
                )
            ],
        ]
    )


def order_delete_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=f"orders:delete_confirm:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Нет, оставить",
                    callback_data=f"orders:view:{order_id}",
                )
            ],
        ]
    )
