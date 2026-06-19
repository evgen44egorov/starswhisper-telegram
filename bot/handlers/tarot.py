import logging
from datetime import date
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import get_settings
from bot.database.models import Order
from bot.database.repositories import complete_order, create_test_order, fail_order, get_profile
from bot.keyboards.main_menu import TAROT_BUTTON, main_menu_keyboard
from bot.keyboards.tarot import (
    CANCEL_TAROT_BUTTON,
    CONFIRM_TAROT_BUTTON,
    PAY_TAROT_BUTTON,
    RESTART_TAROT_BUTTON,
    TAROT_AREAS,
    TAROT_SPREADS,
    tarot_area_keyboard,
    tarot_confirmation_keyboard,
    tarot_needs_profile_keyboard,
    tarot_spread_keyboard,
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
from bot.services.tarot import draw_tarot_cards
from bot.states.tarot import TarotForm
from bot.texts.ru import (
    CRISIS_SUPPORT_TEXT,
    PAYMENT_INVOICE_ERROR_TEXT,
    TAROT_AREA_PROMPT,
    TAROT_CONFIRM_TEXT,
    TAROT_ERROR_TEXT,
    TAROT_GENERATING_TEXT,
    TAROT_NEEDS_PROFILE_TEXT,
    TAROT_QUESTION_PROMPT,
    TAROT_SPREAD_PROMPT,
)
from bot.utils.question import normalize_question
from bot.utils.safety import is_crisis_question
from bot.utils.telegram import escape_and_limit

logger = logging.getLogger(__name__)
router = Router(name="tarot")


async def begin_tarot(source: Message, state: FSMContext, telegram_id: int) -> None:
    await state.clear()
    if await get_profile(telegram_id) is None:
        await show_screen(
            source,
            TAROT_NEEDS_PROFILE_TEXT,
            reply_markup=tarot_needs_profile_keyboard(),
        )
        return
    await state.set_state(TarotForm.spread)
    await show_screen(source, TAROT_SPREAD_PROMPT, reply_markup=tarot_spread_keyboard())


async def show_tarot_confirmation(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    settings = get_settings()
    await state.set_state(TarotForm.confirm)
    await show_screen(
        source,
        TAROT_CONFIRM_TEXT.format(
            spread=escape(str(data["spread"])),
            area=escape(str(data["area"])),
            question=escape(str(data["question"])),
            payment_note=payment_note("tarot_astrology", settings),
        ),
        reply_markup=tarot_confirmation_keyboard(stars_enabled(settings)),
    )


def format_tarot_result(text: str, order: Order, is_demo: bool) -> str:
    return (
        f"{escape_and_limit(text)}\n\n"
        f"<i>Символический расклад · заказ {escape(order.public_id)}</i>"
    )


@router.callback_query(F.data == "service:tarot")
async def begin_tarot_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_tarot(callback.message, state, callback.from_user.id)


@router.message(F.text == TAROT_BUTTON)
async def begin_tarot_message(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_tarot(message, state, message.from_user.id)


@router.callback_query(F.data == "tarot:cancel")
async def cancel_tarot_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "↩️ Расклад отменён.",
            reply_markup=main_menu_keyboard(),
        )


@router.message(
    StateFilter(TarotForm.spread, TarotForm.area, TarotForm.question, TarotForm.confirm),
    F.text == CANCEL_TAROT_BUTTON,
)
async def cancel_tarot_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(message, "↩️ Расклад отменён.", reply_markup=main_menu_keyboard())


@router.message(TarotForm.spread, F.text.in_(set(TAROT_SPREADS)))
async def receive_tarot_spread(message: Message, state: FSMContext) -> None:
    await state.update_data(spread=TAROT_SPREADS[message.text or ""])
    await state.set_state(TarotForm.area)
    await show_screen(message, TAROT_AREA_PROMPT, reply_markup=tarot_area_keyboard())


@router.message(TarotForm.spread)
async def repeat_tarot_spread(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери тип расклада кнопкой.\n\n" + TAROT_SPREAD_PROMPT,
        reply_markup=tarot_spread_keyboard(),
    )


@router.message(TarotForm.area, F.text.in_(set(TAROT_AREAS)))
async def receive_tarot_area(message: Message, state: FSMContext) -> None:
    await state.update_data(area=TAROT_AREAS[message.text or ""])
    await state.set_state(TarotForm.question)
    await show_screen(message, TAROT_QUESTION_PROMPT, reply_markup=ReplyKeyboardRemove())


@router.message(TarotForm.area)
async def repeat_tarot_area(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери тему кнопкой.\n\n" + TAROT_AREA_PROMPT,
        reply_markup=tarot_area_keyboard(),
    )


@router.message(TarotForm.question)
async def receive_tarot_question(message: Message, state: FSMContext) -> None:
    try:
        question = normalize_question(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n{TAROT_QUESTION_PROMPT}",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    if is_crisis_question(question):
        await state.clear()
        await show_screen(
            message,
            CRISIS_SUPPORT_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return
    await state.update_data(question=question)
    await show_tarot_confirmation(message, state)


@router.message(TarotForm.confirm, F.text == RESTART_TAROT_BUTTON)
async def restart_tarot(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_tarot(message, state, message.from_user.id)


@router.message(
    TarotForm.confirm,
    F.text.in_({CONFIRM_TAROT_BUTTON, PAY_TAROT_BUTTON}),
)
async def confirm_tarot(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    profile = await get_profile(message.from_user.id)
    if profile is None:
        await begin_tarot(message, state, message.from_user.id)
        return
    data = await state.get_data()
    cards = draw_tarot_cards()
    input_data = {
        "spread": data["spread"],
        "area": data["area"],
        "question": data["question"],
        "cards": cards,
        "profile": profile_snapshot(profile),
    }
    settings = get_settings()
    if stars_enabled(settings):
        await state.clear()
        try:
            await send_stars_invoice(
                source=message,
                telegram_id=message.from_user.id,
                service_code="tarot_astrology",
                input_data=input_data,
            )
        except PaymentServiceError:
            logger.exception("Не удалось выставить счёт за таро-расклад")
            await show_screen(
                message,
                PAYMENT_INVOICE_ERROR_TEXT,
                reply_markup=main_menu_keyboard(),
            )
        return

    await state.clear()
    progress_message = await show_screen(message, TAROT_GENERATING_TEXT)
    order: Order | None = None
    try:
        order = await create_test_order(
            telegram_id=message.from_user.id,
            service_code="tarot_astrology",
            price_stars=300,
            input_data=input_data,
            public_id_prefix="T",
        )
        result = await AstrobotAIService(settings).generate_tarot_reading(
            profile=profile,
            spread=str(data["spread"]),
            area=str(data["area"]),
            question=str(data["question"]),
            cards=cards,
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
            format_tarot_result(result.text, order, result.is_demo),
            reply_markup=main_menu_keyboard(),
        )
    except AIServiceError:
        logger.exception("Не удалось создать таро-расклад")
        if order is not None:
            await fail_order(order.id, "Ошибка AI-сервиса")
        await show_screen(progress_message, TAROT_ERROR_TEXT, reply_markup=main_menu_keyboard())
    except Exception:
        logger.exception("Непредвиденная ошибка таро-расклада")
        if order is not None:
            await fail_order(order.id, "Внутренняя ошибка")
        await show_screen(progress_message, TAROT_ERROR_TEXT, reply_markup=main_menu_keyboard())


@router.message(TarotForm.confirm)
async def repeat_tarot_confirmation(message: Message, state: FSMContext) -> None:
    await show_tarot_confirmation(message, state)
