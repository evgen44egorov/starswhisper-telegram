import logging
from datetime import date, time
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import get_settings
from bot.database.models import Order
from bot.database.repositories import (
    complete_order,
    create_test_order,
    fail_order,
    get_profile,
)
from bot.keyboards.compatibility import (
    CANCEL_COMPATIBILITY_BUTTON,
    CONFIRM_COMPATIBILITY_BUTTON,
    PAY_COMPATIBILITY_BUTTON,
    RELATIONSHIP_TYPES,
    RESTART_COMPATIBILITY_BUTTON,
    SKIP_PARTNER_PLACE_BUTTON,
    UNKNOWN_PARTNER_DATE_BUTTON,
    UNKNOWN_PARTNER_TIME_BUTTON,
    compatibility_confirmation_keyboard,
    compatibility_needs_profile_keyboard,
    initial_partner_year_page,
    partner_day_keyboard,
    partner_month_keyboard,
    partner_place_keyboard,
    partner_time_keyboard,
    partner_year_keyboard,
    relationship_type_keyboard,
)
from bot.keyboards.main_menu import COMPATIBILITY_BUTTON, main_menu_keyboard
from bot.services.ai import AIServiceError, AstrobotAIService
from bot.services.payments import (
    PaymentServiceError,
    payment_note,
    profile_snapshot,
    send_stars_invoice,
    stars_enabled,
)
from bot.services.screens import show_screen
from bot.states.compatibility import CompatibilityForm
from bot.texts.ru import (
    COMPATIBILITY_CONFIRM_DEMO_TEXT,
    COMPATIBILITY_CONFIRM_OPENAI_TEXT,
    COMPATIBILITY_DATE_PROMPT,
    COMPATIBILITY_DAY_PROMPT,
    COMPATIBILITY_ERROR_TEXT,
    COMPATIBILITY_GENERATING_TEXT,
    COMPATIBILITY_NAME_PROMPT,
    COMPATIBILITY_NEEDS_PROFILE_TEXT,
    COMPATIBILITY_MONTH_PROMPT,
    COMPATIBILITY_PLACE_PROMPT,
    COMPATIBILITY_RELATIONSHIP_PROMPT,
    COMPATIBILITY_TIME_PROMPT,
    PAYMENT_INVOICE_ERROR_TEXT,
)
from bot.utils.profile import (
    normalize_birth_place,
    normalize_name,
    parse_birth_time,
)
from bot.utils.telegram import escape_and_limit

logger = logging.getLogger(__name__)
router = Router(name="compatibility")


async def begin_compatibility(
    source: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    await state.clear()
    profile = await get_profile(telegram_id)
    if profile is None:
        await show_screen(
            source,
            COMPATIBILITY_NEEDS_PROFILE_TEXT,
            reply_markup=compatibility_needs_profile_keyboard(),
        )
        return

    await state.set_state(CompatibilityForm.relationship_type)
    await show_screen(
        source,
        COMPATIBILITY_RELATIONSHIP_PROMPT,
        reply_markup=relationship_type_keyboard(),
    )


def format_compatibility_values(data: dict[str, object]) -> dict[str, str]:
    partner_birth_date = data["partner_birth_date"]
    partner_birth_time = data.get("partner_birth_time")
    return {
        "relationship_type": escape(str(data["relationship_type"])),
        "partner_name": escape(str(data["partner_name"])),
        "partner_birth_date": (
            partner_birth_date.strftime("%d.%m.%Y")
            if isinstance(partner_birth_date, date)
            else "Не указано"
        ),
        "partner_birth_time": (
            partner_birth_time.strftime("%H:%M")
            if isinstance(partner_birth_time, time)
            else "Не указано"
        ),
        "partner_birth_place": (
            escape(str(data["partner_birth_place"]))
            if data.get("partner_birth_place")
            else "Не указано"
        ),
    }


async def ask_partner_place(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(CompatibilityForm.partner_birth_place)
    await show_screen(
        source,
        COMPATIBILITY_PLACE_PROMPT.format(name=escape(data["partner_name"])),
        reply_markup=partner_place_keyboard(),
    )


async def show_partner_birth_year(
    source: Message,
    state: FSMContext,
    page_start: int | None = None,
) -> None:
    data = await state.get_data()
    page_start = page_start if page_start is not None else initial_partner_year_page()
    current_year = date.today().year
    end_year = min(page_start + 15, current_year)
    await state.set_state(CompatibilityForm.partner_birth_year)
    await show_screen(
        source,
        COMPATIBILITY_DATE_PROMPT.format(
            name=escape(str(data["partner_name"])),
            start_year=page_start,
            end_year=end_year,
        ),
        reply_markup=partner_year_keyboard(page_start),
    )


async def ask_partner_time(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(CompatibilityForm.partner_birth_time)
    await show_screen(
        source,
        COMPATIBILITY_TIME_PROMPT.format(name=escape(str(data["partner_name"]))),
        reply_markup=partner_time_keyboard(),
    )


async def show_compatibility_confirmation(
    source: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    settings = get_settings()
    template = (
        COMPATIBILITY_CONFIRM_DEMO_TEXT
        if settings.ai_provider.strip().lower() == "demo"
        else COMPATIBILITY_CONFIRM_OPENAI_TEXT
    )
    await state.set_state(CompatibilityForm.confirm)
    await show_screen(
        source,
        template.format(
            **format_compatibility_values(data),
            payment_note=payment_note("compatibility", settings),
        ),
        reply_markup=compatibility_confirmation_keyboard(stars_enabled(settings)),
    )


def format_compatibility_result(text: str, order: Order, is_demo: bool) -> str:
    return (
        f"{escape_and_limit(text)}\n\n"
        f"<i>Заказ {escape(order.public_id)} · "
        "совместимость не является гарантией развития отношений.</i>"
    )


@router.callback_query(F.data == "service:compatibility")
async def begin_compatibility_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_compatibility(callback.message, state, callback.from_user.id)


@router.message(F.text == COMPATIBILITY_BUTTON)
async def begin_compatibility_message(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_compatibility(message, state, message.from_user.id)


@router.callback_query(F.data == "compatibility:cancel")
async def cancel_compatibility_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
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
        CompatibilityForm.relationship_type,
        CompatibilityForm.partner_name,
        CompatibilityForm.partner_birth_year,
        CompatibilityForm.partner_birth_month,
        CompatibilityForm.partner_birth_day,
        CompatibilityForm.partner_birth_time,
        CompatibilityForm.partner_birth_place,
        CompatibilityForm.confirm,
    ),
    F.text == CANCEL_COMPATIBILITY_BUTTON,
)
async def cancel_compatibility_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        message,
        "↩️ Разбор совместимости отменен.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(
    CompatibilityForm.relationship_type,
    F.text.in_(set(RELATIONSHIP_TYPES)),
)
async def receive_relationship_type(message: Message, state: FSMContext) -> None:
    relationship_type = RELATIONSHIP_TYPES[message.text or ""]
    await state.update_data(relationship_type=relationship_type)
    await state.set_state(CompatibilityForm.partner_name)
    await show_screen(
        message,
        COMPATIBILITY_NAME_PROMPT,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(CompatibilityForm.relationship_type)
async def repeat_relationship_type(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери тип отношений на клавиатуре.\n\n"
        + COMPATIBILITY_RELATIONSHIP_PROMPT,
        reply_markup=relationship_type_keyboard(),
    )


@router.message(CompatibilityForm.partner_name)
async def receive_partner_name(message: Message, state: FSMContext) -> None:
    try:
        partner_name = normalize_name(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n{COMPATIBILITY_NAME_PROMPT}",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(partner_name=partner_name)
    await show_partner_birth_year(message, state)


@router.callback_query(
    CompatibilityForm.partner_birth_year,
    F.data.startswith("compatibility:years:"),
)
async def change_partner_year_page(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        page_start = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    if isinstance(callback.message, Message):
        await show_partner_birth_year(callback.message, state, page_start)


@router.callback_query(
    CompatibilityForm.partner_birth_year,
    F.data.startswith("compatibility:year:"),
)
async def select_partner_year(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        year = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    current_year = date.today().year
    if not current_year - 120 <= year <= current_year:
        return
    await state.update_data(partner_birth_year=year)
    await state.set_state(CompatibilityForm.partner_birth_month)
    if isinstance(callback.message, Message):
        data = await state.get_data()
        await show_screen(
            callback.message,
            COMPATIBILITY_MONTH_PROMPT.format(
                name=escape(str(data["partner_name"])),
                year=year,
            ),
            reply_markup=partner_month_keyboard(year),
        )


@router.callback_query(
    CompatibilityForm.partner_birth_month,
    F.data == "compatibility:year_back",
)
async def partner_year_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_partner_birth_year(callback.message, state)


@router.callback_query(
    CompatibilityForm.partner_birth_month,
    F.data.startswith("compatibility:month:"),
)
async def select_partner_month(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        month = int((callback.data or "").rsplit(":", 1)[1])
        data = await state.get_data()
        year = int(data["partner_birth_year"])
    except (IndexError, KeyError, TypeError, ValueError):
        return
    if not 1 <= month <= 12:
        return
    if year == date.today().year and month > date.today().month:
        return
    await state.update_data(partner_birth_month=month)
    await state.set_state(CompatibilityForm.partner_birth_day)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            COMPATIBILITY_DAY_PROMPT.format(
                name=escape(str(data["partner_name"])),
                year=year,
                month=month,
            ),
            reply_markup=partner_day_keyboard(year, month),
        )


@router.callback_query(
    CompatibilityForm.partner_birth_day,
    F.data == "compatibility:month_back",
)
async def partner_month_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    year = int(data["partner_birth_year"])
    await state.set_state(CompatibilityForm.partner_birth_month)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            COMPATIBILITY_MONTH_PROMPT.format(
                name=escape(str(data["partner_name"])),
                year=year,
            ),
            reply_markup=partner_month_keyboard(year),
        )


@router.callback_query(
    CompatibilityForm.partner_birth_day,
    F.data.startswith("compatibility:day:"),
)
async def select_partner_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        day = int((callback.data or "").rsplit(":", 1)[1])
        data = await state.get_data()
        partner_birth_date = date(
            int(data["partner_birth_year"]),
            int(data["partner_birth_month"]),
            day,
        )
    except (IndexError, KeyError, TypeError, ValueError):
        return
    if partner_birth_date > date.today():
        return

    await state.update_data(partner_birth_date=partner_birth_date)
    if isinstance(callback.message, Message):
        await ask_partner_time(callback.message, state)


@router.callback_query(
    StateFilter(
        CompatibilityForm.partner_birth_year,
        CompatibilityForm.partner_birth_month,
        CompatibilityForm.partner_birth_day,
    ),
    F.data == "compatibility:date_unknown",
)
async def skip_partner_birth_date(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(partner_birth_date=None, partner_birth_time=None)
    if isinstance(callback.message, Message):
        await ask_partner_place(callback.message, state)


@router.message(
    StateFilter(
        CompatibilityForm.partner_birth_year,
        CompatibilityForm.partner_birth_month,
        CompatibilityForm.partner_birth_day,
    )
)
async def repeat_partner_birth_date_buttons(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    current_state = await state.get_state()
    warning = f"⚠️ Выбери дату кнопками или нажми «{UNKNOWN_PARTNER_DATE_BUTTON}».\n\n"
    if current_state == CompatibilityForm.partner_birth_month.state:
        year = int(data["partner_birth_year"])
        await show_screen(
            message,
            warning + COMPATIBILITY_MONTH_PROMPT.format(
                name=escape(str(data["partner_name"])), year=year
            ),
            reply_markup=partner_month_keyboard(year),
        )
    elif current_state == CompatibilityForm.partner_birth_day.state:
        year = int(data["partner_birth_year"])
        month = int(data["partner_birth_month"])
        await show_screen(
            message,
            warning + COMPATIBILITY_DAY_PROMPT.format(
                name=escape(str(data["partner_name"])), year=year, month=month
            ),
            reply_markup=partner_day_keyboard(year, month),
        )
    else:
        await show_partner_birth_year(message, state)


@router.message(
    CompatibilityForm.partner_birth_time,
    F.text == UNKNOWN_PARTNER_TIME_BUTTON,
)
async def skip_partner_birth_time(message: Message, state: FSMContext) -> None:
    await state.update_data(partner_birth_time=None)
    await ask_partner_place(message, state)


@router.message(CompatibilityForm.partner_birth_time)
async def receive_partner_birth_time(message: Message, state: FSMContext) -> None:
    try:
        partner_birth_time = parse_birth_time(message.text or "")
    except ValueError as error:
        data = await state.get_data()
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n"
            + COMPATIBILITY_TIME_PROMPT.format(
                name=escape(data["partner_name"])
            ),
            reply_markup=partner_time_keyboard(),
        )
        return

    await state.update_data(partner_birth_time=partner_birth_time)
    await ask_partner_place(message, state)


@router.message(
    CompatibilityForm.partner_birth_place,
    F.text == SKIP_PARTNER_PLACE_BUTTON,
)
async def skip_partner_birth_place(message: Message, state: FSMContext) -> None:
    await state.update_data(partner_birth_place=None)
    await show_compatibility_confirmation(message, state)


@router.message(CompatibilityForm.partner_birth_place)
async def receive_partner_birth_place(message: Message, state: FSMContext) -> None:
    try:
        partner_birth_place = normalize_birth_place(message.text or "")
    except ValueError as error:
        data = await state.get_data()
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n"
            + COMPATIBILITY_PLACE_PROMPT.format(
                name=escape(data["partner_name"])
            ),
            reply_markup=partner_place_keyboard(),
        )
        return

    await state.update_data(partner_birth_place=partner_birth_place)
    await show_compatibility_confirmation(message, state)


@router.message(
    CompatibilityForm.confirm,
    F.text == RESTART_COMPATIBILITY_BUTTON,
)
async def restart_compatibility(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_compatibility(message, state, message.from_user.id)


@router.message(
    CompatibilityForm.confirm,
    F.text.in_({CONFIRM_COMPATIBILITY_BUTTON, PAY_COMPATIBILITY_BUTTON}),
)
async def confirm_compatibility(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    profile = await get_profile(message.from_user.id)
    if profile is None:
        await begin_compatibility(message, state, message.from_user.id)
        return

    partner_birth_date = data.get("partner_birth_date")
    partner_birth_time = data.get("partner_birth_time")
    partner_birth_time_text = (
        partner_birth_time.strftime("%H:%M")
        if isinstance(partner_birth_time, time)
        else None
    )
    settings = get_settings()
    compatibility_input = {
        "relationship_type": data["relationship_type"],
        "partner_name": data["partner_name"],
        "partner_birth_date": (
            partner_birth_date.isoformat()
            if isinstance(partner_birth_date, date)
            else None
        ),
        "partner_birth_time": partner_birth_time_text,
        "partner_birth_place": data.get("partner_birth_place"),
        "profile": profile_snapshot(profile),
    }
    if stars_enabled(settings):
        await state.clear()
        try:
            await send_stars_invoice(
                source=message,
                telegram_id=message.from_user.id,
                service_code="compatibility",
                input_data=compatibility_input,
            )
        except PaymentServiceError:
            logger.exception("Не удалось выставить счёт за совместимость")
            await show_screen(
                message,
                PAYMENT_INVOICE_ERROR_TEXT,
                reply_markup=main_menu_keyboard(),
            )
        return

    await state.clear()
    progress_message = await show_screen(message, COMPATIBILITY_GENERATING_TEXT)
    order: Order | None = None
    try:
        order = await create_test_order(
            telegram_id=message.from_user.id,
            service_code="compatibility",
            price_stars=600,
            input_data=compatibility_input,
            public_id_prefix="C",
        )
        result = await AstrobotAIService(get_settings()).generate_compatibility(
            profile=profile,
            relationship_type=data["relationship_type"],
            partner_name=data["partner_name"],
            partner_birth_date=partner_birth_date,
            partner_birth_time=partner_birth_time_text,
            partner_birth_place=data.get("partner_birth_place"),
            current_date=date.today(),
        )
        await complete_order(order.id, result.text, result.provider, result.model)
        await show_screen(
            progress_message,
            format_compatibility_result(result.text, order, result.is_demo),
            reply_markup=main_menu_keyboard(),
        )
    except AIServiceError:
        logger.exception("Не удалось создать разбор совместимости")
        if order is not None:
            await fail_order(order.id, "Ошибка AI-сервиса")
        await show_screen(
            progress_message,
            COMPATIBILITY_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Непредвиденная ошибка разбора совместимости")
        if order is not None:
            await fail_order(order.id, "Внутренняя ошибка")
        await show_screen(
            progress_message,
            COMPATIBILITY_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.message(CompatibilityForm.confirm)
async def repeat_compatibility_confirmation(
    message: Message,
    state: FSMContext,
) -> None:
    await show_compatibility_confirmation(message, state)
