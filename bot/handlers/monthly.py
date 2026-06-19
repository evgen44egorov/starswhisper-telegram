import logging
from datetime import date
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.database.models import Order
from bot.database.repositories import (
    complete_order,
    create_test_order,
    fail_order,
    get_profile,
)
from bot.keyboards.main_menu import MONTH_BUTTON, main_menu_keyboard
from bot.keyboards.monthly import (
    CANCEL_MONTHLY_BUTTON,
    CONFIRM_MONTHLY_BUTTON,
    MONTH_AREAS,
    MONTH_PERIODS,
    NEXT_MONTH_BUTTON,
    PAY_MONTHLY_BUTTON,
    RESTART_MONTHLY_BUTTON,
    month_area_keyboard,
    month_period_keyboard,
    monthly_confirmation_keyboard,
    monthly_needs_profile_keyboard,
)
from bot.services.ai import AIServiceError, AstrobotAIService
from bot.services.payments import (
    PaymentServiceError,
    payment_note,
    profile_snapshot,
    send_stars_invoice,
    stars_enabled,
)
from bot.services.screens import show_screen
from bot.states.monthly import MonthlyForecastForm
from bot.texts.ru import (
    MONTHLY_AREA_PROMPT,
    MONTHLY_CONFIRM_DEMO_TEXT,
    MONTHLY_CONFIRM_OPENAI_TEXT,
    MONTHLY_ERROR_TEXT,
    MONTHLY_GENERATING_TEXT,
    MONTHLY_NEEDS_PROFILE_TEXT,
    MONTHLY_PERIOD_PROMPT,
    PAYMENT_INVOICE_ERROR_TEXT,
)
from bot.utils.months import first_day_of_next_month, format_month_period
from bot.utils.telegram import escape_and_limit

logger = logging.getLogger(__name__)
router = Router(name="monthly")


async def begin_monthly_forecast(
    source: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    await state.clear()
    profile = await get_profile(telegram_id)
    if profile is None:
        await show_screen(
            source,
            MONTHLY_NEEDS_PROFILE_TEXT,
            reply_markup=monthly_needs_profile_keyboard(),
        )
        return

    await state.set_state(MonthlyForecastForm.period)
    await show_screen(
        source,
        MONTHLY_PERIOD_PROMPT,
        reply_markup=month_period_keyboard(),
    )


async def show_monthly_confirmation(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    settings = get_settings()
    template = (
        MONTHLY_CONFIRM_DEMO_TEXT
        if settings.ai_provider.strip().lower() == "demo"
        else MONTHLY_CONFIRM_OPENAI_TEXT
    )
    await state.set_state(MonthlyForecastForm.confirm)
    await show_screen(
        source,
        template.format(
            period=escape(data["period_label"]),
            area=escape(data["area"]),
            payment_note=payment_note("monthly_forecast", settings),
        ),
        reply_markup=monthly_confirmation_keyboard(stars_enabled(settings)),
    )


def format_monthly_result(text: str, order: Order, is_demo: bool) -> str:
    return (
        f"{escape_and_limit(text)}\n\n"
        f"<i>Заказ {escape(order.public_id)} · "
        "прогноз носит развлекательный и саморефлексивный характер.</i>"
    )


@router.callback_query(F.data == "service:month")
async def begin_monthly_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_monthly_forecast(callback.message, state, callback.from_user.id)


@router.message(F.text == MONTH_BUTTON)
async def begin_monthly_message(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_monthly_forecast(message, state, message.from_user.id)


@router.callback_query(F.data == "monthly:cancel")
async def cancel_monthly_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "✨ Что хочешь узнать сейчас?",
            reply_markup=main_menu_keyboard(),
        )


@router.message(
    StateFilter(
        MonthlyForecastForm.period,
        MonthlyForecastForm.area,
        MonthlyForecastForm.confirm,
    ),
    F.text == CANCEL_MONTHLY_BUTTON,
)
async def cancel_monthly_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        message,
        "↩️ Прогноз на месяц отменен.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(MonthlyForecastForm.period, F.text.in_(MONTH_PERIODS))
async def receive_month_period(message: Message, state: FSMContext) -> None:
    today = date.today()
    target_month = today.replace(day=1)
    if message.text == NEXT_MONTH_BUTTON:
        target_month = first_day_of_next_month(today)

    await state.update_data(
        period_key=target_month.strftime("%Y-%m"),
        period_label=format_month_period(target_month),
    )
    await state.set_state(MonthlyForecastForm.area)
    await show_screen(
        message,
        MONTHLY_AREA_PROMPT,
        reply_markup=month_area_keyboard(),
    )


@router.message(MonthlyForecastForm.period)
async def repeat_month_period(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери период на клавиатуре.\n\n" + MONTHLY_PERIOD_PROMPT,
        reply_markup=month_period_keyboard(),
    )


@router.message(MonthlyForecastForm.area, F.text.in_(set(MONTH_AREAS)))
async def receive_month_area(message: Message, state: FSMContext) -> None:
    await state.update_data(area=MONTH_AREAS[message.text or ""])
    await show_monthly_confirmation(message, state)


@router.message(MonthlyForecastForm.area)
async def repeat_month_area(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери основной фокус на клавиатуре.\n\n" + MONTHLY_AREA_PROMPT,
        reply_markup=month_area_keyboard(),
    )


@router.message(MonthlyForecastForm.confirm, F.text == RESTART_MONTHLY_BUTTON)
async def restart_monthly(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_monthly_forecast(message, state, message.from_user.id)


@router.message(
    MonthlyForecastForm.confirm,
    F.text.in_({CONFIRM_MONTHLY_BUTTON, PAY_MONTHLY_BUTTON}),
)
async def confirm_monthly(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    profile = await get_profile(message.from_user.id)
    if profile is None:
        await begin_monthly_forecast(message, state, message.from_user.id)
        return

    settings = get_settings()
    monthly_input = {
        "period_key": data["period_key"],
        "period_label": data["period_label"],
        "area": data["area"],
        "profile": profile_snapshot(profile),
    }
    if stars_enabled(settings):
        await state.clear()
        try:
            await send_stars_invoice(
                source=message,
                telegram_id=message.from_user.id,
                service_code="monthly_forecast",
                input_data=monthly_input,
            )
        except PaymentServiceError:
            logger.exception("Не удалось выставить счёт за прогноз на месяц")
            await show_screen(
                message,
                PAYMENT_INVOICE_ERROR_TEXT,
                reply_markup=main_menu_keyboard(),
            )
        return

    await state.clear()
    progress_message = await show_screen(message, MONTHLY_GENERATING_TEXT)
    order: Order | None = None
    try:
        order = await create_test_order(
            telegram_id=message.from_user.id,
            service_code="monthly_forecast",
            price_stars=400,
            input_data=monthly_input,
            public_id_prefix="M",
        )
        result = await AstrobotAIService(get_settings()).generate_monthly_forecast(
            profile=profile,
            period=data["period_label"],
            area=data["area"],
            current_date=date.today(),
        )
        await complete_order(order.id, result.text, result.provider, result.model)
        await show_screen(
            progress_message,
            format_monthly_result(result.text, order, result.is_demo),
            reply_markup=main_menu_keyboard(),
        )
    except AIServiceError:
        logger.exception("Не удалось создать прогноз на месяц")
        if order is not None:
            await fail_order(order.id, "Ошибка AI-сервиса")
        await show_screen(
            progress_message,
            MONTHLY_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Непредвиденная ошибка прогноза на месяц")
        if order is not None:
            await fail_order(order.id, "Внутренняя ошибка")
        await show_screen(
            progress_message,
            MONTHLY_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.message(MonthlyForecastForm.confirm)
async def repeat_monthly_confirmation(message: Message, state: FSMContext) -> None:
    await show_monthly_confirmation(message, state)
