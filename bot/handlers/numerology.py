import logging
from datetime import date
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.database.models import Order
from bot.database.repositories import complete_order, create_test_order, fail_order, get_profile
from bot.keyboards.main_menu import NUMEROLOGY_BUTTON, main_menu_keyboard
from bot.keyboards.numerology import (
    CANCEL_NUMEROLOGY_BUTTON,
    CONFIRM_NUMEROLOGY_BUTTON,
    NUMEROLOGY_PERIODS,
    PAY_NUMEROLOGY_BUTTON,
    RESTART_NUMEROLOGY_BUTTON,
    numerology_confirmation_keyboard,
    numerology_needs_profile_keyboard,
    numerology_period_keyboard,
)
from bot.services.ai import AIServiceError, AstrobotAIService
from bot.services.numerology import calculate_numerology
from bot.services.payments import (
    PaymentServiceError,
    payment_note,
    profile_snapshot,
    send_stars_invoice,
    stars_enabled,
)
from bot.services.screens import show_screen
from bot.states.numerology import NumerologyForm
from bot.texts.ru import (
    NUMEROLOGY_CONFIRM_TEXT,
    NUMEROLOGY_ERROR_TEXT,
    NUMEROLOGY_GENERATING_TEXT,
    NUMEROLOGY_NEEDS_PROFILE_TEXT,
    NUMEROLOGY_PERIOD_PROMPT,
    PAYMENT_INVOICE_ERROR_TEXT,
)
from bot.utils.telegram import escape_and_limit

logger = logging.getLogger(__name__)
router = Router(name="numerology")


async def begin_numerology(source: Message, state: FSMContext, telegram_id: int) -> None:
    await state.clear()
    if await get_profile(telegram_id) is None:
        await show_screen(
            source,
            NUMEROLOGY_NEEDS_PROFILE_TEXT,
            reply_markup=numerology_needs_profile_keyboard(),
        )
        return
    await state.set_state(NumerologyForm.period)
    await show_screen(
        source,
        NUMEROLOGY_PERIOD_PROMPT,
        reply_markup=numerology_period_keyboard(),
    )


async def show_numerology_confirmation(
    source: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    profile = await get_profile(telegram_id)
    if profile is None:
        await begin_numerology(source, state, telegram_id)
        return
    data = await state.get_data()
    numbers = calculate_numerology(profile.birth_date, date.today())
    await state.update_data(numbers=numbers)
    settings = get_settings()
    await state.set_state(NumerologyForm.confirm)
    await show_screen(
        source,
        NUMEROLOGY_CONFIRM_TEXT.format(
            period=escape(str(data["period"])),
            payment_note=payment_note("numerology", settings),
            **numbers,
        ),
        reply_markup=numerology_confirmation_keyboard(stars_enabled(settings)),
    )


def format_numerology_result(text: str, order: Order, is_demo: bool) -> str:
    return (
        f"{escape_and_limit(text)}\n\n"
        f"<i>Нумерологический разбор · заказ {escape(order.public_id)}</i>"
    )


@router.callback_query(F.data == "service:numerology")
async def begin_numerology_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_numerology(callback.message, state, callback.from_user.id)


@router.message(F.text == NUMEROLOGY_BUTTON)
async def begin_numerology_message(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_numerology(message, state, message.from_user.id)


@router.callback_query(F.data == "numerology:cancel")
async def cancel_numerology_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "↩️ Нумерологический разбор отменён.",
            reply_markup=main_menu_keyboard(),
        )


@router.message(
    StateFilter(NumerologyForm.period, NumerologyForm.confirm),
    F.text == CANCEL_NUMEROLOGY_BUTTON,
)
async def cancel_numerology_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        message,
        "↩️ Нумерологический разбор отменён.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(NumerologyForm.period, F.text.in_(set(NUMEROLOGY_PERIODS)))
async def receive_numerology_period(message: Message, state: FSMContext) -> None:
    await state.update_data(period=NUMEROLOGY_PERIODS[message.text or ""])
    if message.from_user is not None:
        await show_numerology_confirmation(message, state, message.from_user.id)


@router.message(NumerologyForm.period)
async def repeat_numerology_period(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери период кнопкой.\n\n" + NUMEROLOGY_PERIOD_PROMPT,
        reply_markup=numerology_period_keyboard(),
    )


@router.message(NumerologyForm.confirm, F.text == RESTART_NUMEROLOGY_BUTTON)
async def restart_numerology(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_numerology(message, state, message.from_user.id)


@router.message(
    NumerologyForm.confirm,
    F.text.in_({CONFIRM_NUMEROLOGY_BUTTON, PAY_NUMEROLOGY_BUTTON}),
)
async def confirm_numerology(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    profile = await get_profile(message.from_user.id)
    if profile is None:
        await begin_numerology(message, state, message.from_user.id)
        return
    data = await state.get_data()
    numbers = {key: int(value) for key, value in dict(data["numbers"]).items()}
    input_data = {
        "period": data["period"],
        "numbers": numbers,
        "profile": profile_snapshot(profile),
    }
    settings = get_settings()
    if stars_enabled(settings):
        await state.clear()
        try:
            await send_stars_invoice(
                source=message,
                telegram_id=message.from_user.id,
                service_code="numerology",
                input_data=input_data,
            )
        except PaymentServiceError:
            logger.exception("Не удалось выставить счёт за нумерологию")
            await show_screen(
                message,
                PAYMENT_INVOICE_ERROR_TEXT,
                reply_markup=main_menu_keyboard(),
            )
        return

    await state.clear()
    progress_message = await show_screen(message, NUMEROLOGY_GENERATING_TEXT)
    order: Order | None = None
    try:
        order = await create_test_order(
            telegram_id=message.from_user.id,
            service_code="numerology",
            price_stars=250,
            input_data=input_data,
            public_id_prefix="U",
        )
        result = await AstrobotAIService(settings).generate_numerology(
            profile=profile,
            period=str(data["period"]),
            numbers=numbers,
            current_date=date.today(),
        )
        await complete_order(
            order_id=order.id,
            result_text=result.text,
            provider=result.provider,
            model=result.model,
        )
        await show_screen(
            progress_message,
            format_numerology_result(result.text, order, result.is_demo),
            reply_markup=main_menu_keyboard(),
        )
    except AIServiceError:
        logger.exception("Не удалось создать нумерологический разбор")
        if order is not None:
            await fail_order(order.id, "Ошибка AI-сервиса")
        await show_screen(
            progress_message,
            NUMEROLOGY_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Непредвиденная ошибка нумерологии")
        if order is not None:
            await fail_order(order.id, "Внутренняя ошибка")
        await show_screen(
            progress_message,
            NUMEROLOGY_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.message(NumerologyForm.confirm)
async def repeat_numerology_confirmation(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await show_numerology_confirmation(message, state, message.from_user.id)
