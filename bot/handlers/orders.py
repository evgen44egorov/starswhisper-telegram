from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.repositories import (
    delete_user_order,
    get_user_order,
    get_user_order_payment,
    list_user_orders,
)
from bot.keyboards.main_menu import ORDERS_BUTTON, main_menu_keyboard
from bot.keyboards.orders import (
    order_actions_keyboard,
    order_delete_keyboard,
    order_result_keyboard,
    orders_list_keyboard,
)
from bot.services.orders import format_order_card, service_label
from bot.services.payments import PaymentServiceError, send_existing_stars_invoice
from bot.services.screens import show_screen
from bot.texts.ru import (
    ORDERS_EMPTY_TEXT,
    ORDERS_LIST_TEXT,
    ORDER_DELETED_TEXT,
    ORDER_DELETE_CONFIRM_TEXT,
    ORDER_NOT_FOUND_TEXT,
)
from bot.utils.telegram import escape_and_limit

router = Router(name="orders")


def extract_order_id(callback_data: str | None) -> int | None:
    if not callback_data:
        return None
    try:
        return int(callback_data.rsplit(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        return None


async def show_orders_list(source: Message, telegram_id: int) -> None:
    orders = await list_user_orders(telegram_id)
    if not orders:
        await show_screen(
            source,
            ORDERS_EMPTY_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    await show_screen(
        source,
        ORDERS_LIST_TEXT,
        reply_markup=orders_list_keyboard(orders),
    )


async def show_order_or_not_found(
    source: Message,
    telegram_id: int,
    order_id: int | None,
) -> None:
    order = (
        await get_user_order(telegram_id, order_id)
        if order_id is not None
        else None
    )
    if order is None:
        await show_screen(
            source,
            ORDER_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    await show_screen(
        source,
        format_order_card(order),
        reply_markup=order_actions_keyboard(order),
    )


@router.message(F.text == ORDERS_BUTTON)
async def orders_message(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
    await show_orders_list(message, message.from_user.id)


@router.callback_query(F.data == "orders:list")
async def orders_list_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_orders_list(callback.message, callback.from_user.id)


@router.callback_query(F.data.startswith("orders:view:"))
async def order_view_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_order_or_not_found(
            callback.message,
            callback.from_user.id,
            extract_order_id(callback.data),
        )


@router.callback_query(F.data.startswith("orders:result:"))
async def order_result_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    order_id = extract_order_id(callback.data)
    order = (
        await get_user_order(callback.from_user.id, order_id)
        if order_id is not None
        else None
    )
    if order is None or not order.result_text:
        await show_screen(
            callback.message,
            ORDER_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    demo_note = (
        "\n\n<i>🧪 Результат создан демонстрационным генератором.</i>"
        if order.provider == "demo"
        else ""
    )
    await show_screen(
        callback.message,
        f"{escape_and_limit(order.result_text)}{demo_note}\n\n"
        f"<i>{service_label(order.service_code)} · {escape(order.public_id)}</i>",
        reply_markup=order_result_keyboard(order.id),
    )


@router.callback_query(F.data.startswith("orders:pay:"))
async def order_pay_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    order_id = extract_order_id(callback.data)
    order = (
        await get_user_order(callback.from_user.id, order_id)
        if order_id is not None
        else None
    )
    payment = (
        await get_user_order_payment(callback.from_user.id, order_id)
        if order_id is not None
        else None
    )
    if order is None or payment is None:
        await show_screen(
            callback.message,
            ORDER_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return
    try:
        await send_existing_stars_invoice(callback.message, order, payment)
    except PaymentServiceError:
        await show_screen(
            callback.message,
            "⚠️ Не удалось повторно открыть счёт. Используй /paysupport.",
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("orders:delete:"))
async def order_delete_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    order_id = extract_order_id(callback.data)
    order = (
        await get_user_order(callback.from_user.id, order_id)
        if order_id is not None
        else None
    )
    if order is None:
        await show_screen(
            callback.message,
            ORDER_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    await show_screen(
        callback.message,
        ORDER_DELETE_CONFIRM_TEXT.format(public_id=escape(order.public_id)),
        reply_markup=order_delete_keyboard(order.id),
    )


@router.callback_query(F.data.startswith("orders:delete_confirm:"))
async def order_delete_confirm_callback(callback: CallbackQuery) -> None:
    order_id = extract_order_id(callback.data)
    deleted = (
        await delete_user_order(callback.from_user.id, order_id)
        if order_id is not None
        else False
    )
    await callback.answer("Заказ удалён" if deleted else "Заказ не найден")
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            ORDER_DELETED_TEXT if deleted else ORDER_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "orders:menu")
async def orders_menu_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "✨ Что хочешь узнать сейчас?",
            reply_markup=main_menu_keyboard(),
        )
