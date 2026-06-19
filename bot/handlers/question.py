import logging
from datetime import date
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import get_settings
from bot.database.models import Order
from bot.database.repositories import (
    complete_question_order,
    create_question_order,
    fail_question_order,
    get_profile,
)
from bot.keyboards.main_menu import QUESTION_BUTTON, main_menu_keyboard
from bot.keyboards.question import (
    CANCEL_QUESTION_BUTTON,
    CONFIRM_QUESTION_BUTTON,
    EDIT_QUESTION_BUTTON,
    PAY_QUESTION_BUTTON,
    QUESTION_AREAS,
    question_area_keyboard,
    question_confirmation_keyboard,
    question_needs_profile_keyboard,
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
from bot.states.question import QuestionForm
from bot.texts.ru import (
    CRISIS_SUPPORT_TEXT,
    PAYMENT_INVOICE_ERROR_TEXT,
    QUESTION_AREA_PROMPT,
    QUESTION_CONFIRM_DEMO_TEXT,
    QUESTION_CONFIRM_OPENAI_TEXT,
    QUESTION_ERROR_TEXT,
    QUESTION_GENERATING_TEXT,
    QUESTION_NEEDS_PROFILE_TEXT,
    QUESTION_TEXT_PROMPT,
)
from bot.utils.question import normalize_question
from bot.utils.safety import is_crisis_question
from bot.utils.telegram import escape_and_limit

logger = logging.getLogger(__name__)
router = Router(name="question")


async def begin_question(
    source: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    await state.clear()
    profile = await get_profile(telegram_id)
    if profile is None:
        await show_screen(
            source,
            QUESTION_NEEDS_PROFILE_TEXT,
            reply_markup=question_needs_profile_keyboard(),
        )
        return

    await state.set_state(QuestionForm.area)
    await show_screen(
        source,
        QUESTION_AREA_PROMPT,
        reply_markup=question_area_keyboard(),
    )


async def show_question_confirmation(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    settings = get_settings()
    template = (
        QUESTION_CONFIRM_DEMO_TEXT
        if settings.ai_provider.strip().lower() == "demo"
        else QUESTION_CONFIRM_OPENAI_TEXT
    )
    await state.set_state(QuestionForm.confirm)
    await show_screen(
        source,
        template.format(
            area=escape(data["area"]),
            question=escape(data["question"]),
            payment_note=payment_note("personal_question", settings),
        ),
        reply_markup=question_confirmation_keyboard(stars_enabled(settings)),
    )


def format_question_result(text: str, order: Order, is_demo: bool) -> str:
    demo_note = (
        "\n\n<i>🧪 Ответ создан локальным демонстрационным генератором.</i>"
        if is_demo
        else ""
    )
    return (
        f"{escape_and_limit(text)}{demo_note}\n\n"
        f"<i>Тестовый заказ: {escape(order.public_id)} · "
        "развлекательный и саморефлексивный разбор.</i>"
    )


@router.callback_query(F.data == "service:question")
async def begin_question_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_question(callback.message, state, callback.from_user.id)


@router.message(F.text == QUESTION_BUTTON)
async def begin_question_message(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await begin_question(message, state, message.from_user.id)


@router.callback_query(F.data == "question:cancel")
async def cancel_question_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "✨ Что хочешь узнать сейчас?",
            reply_markup=main_menu_keyboard(),
        )


@router.message(
    StateFilter(QuestionForm.area, QuestionForm.text, QuestionForm.confirm),
    F.text == CANCEL_QUESTION_BUTTON,
)
async def cancel_question_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        message,
        "↩️ Личный вопрос отменен.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(QuestionForm.area, F.text.in_(set(QUESTION_AREAS)))
async def receive_question_area(message: Message, state: FSMContext) -> None:
    area = QUESTION_AREAS[message.text or ""]
    await state.update_data(area=area)
    await state.set_state(QuestionForm.text)
    await show_screen(
        message,
        QUESTION_TEXT_PROMPT,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(QuestionForm.area)
async def repeat_question_area(message: Message) -> None:
    await show_screen(
        message,
        "⚠️ Выбери одну из сфер на клавиатуре.\n\n" + QUESTION_AREA_PROMPT,
        reply_markup=question_area_keyboard(),
    )


@router.message(QuestionForm.text)
async def receive_question_text(message: Message, state: FSMContext) -> None:
    try:
        question = normalize_question(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n{QUESTION_TEXT_PROMPT}",
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
    await show_question_confirmation(message, state)


@router.message(QuestionForm.confirm, F.text == EDIT_QUESTION_BUTTON)
async def edit_question(message: Message, state: FSMContext) -> None:
    await state.set_state(QuestionForm.text)
    await show_screen(
        message,
        QUESTION_TEXT_PROMPT,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(
    QuestionForm.confirm,
    F.text.in_({CONFIRM_QUESTION_BUTTON, PAY_QUESTION_BUTTON}),
)
async def confirm_question(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    profile = await get_profile(message.from_user.id)
    if profile is None:
        await begin_question(message, state, message.from_user.id)
        return

    settings = get_settings()
    if stars_enabled(settings):
        await state.clear()
        try:
            await send_stars_invoice(
                source=message,
                telegram_id=message.from_user.id,
                service_code="personal_question",
                input_data={
                    "area": data["area"],
                    "question": data["question"],
                    "profile": profile_snapshot(profile),
                },
            )
        except PaymentServiceError:
            logger.exception("Не удалось выставить счёт за личный вопрос")
            await show_screen(
                message,
                PAYMENT_INVOICE_ERROR_TEXT,
                reply_markup=main_menu_keyboard(),
            )
        return

    await state.clear()
    progress_message = await show_screen(message, QUESTION_GENERATING_TEXT)
    order: Order | None = None
    try:
        order = await create_question_order(
            telegram_id=message.from_user.id,
            question_area=data["area"],
            question_text=data["question"],
        )
        result = await AstrobotAIService(get_settings()).generate_personal_question(
            profile=profile,
            question_area=data["area"],
            question_text=data["question"],
            current_date=date.today(),
        )
        await complete_question_order(
            order_id=order.id,
            result_text=result.text,
            provider=result.provider,
            model=result.model,
        )
        await show_screen(
            progress_message,
            format_question_result(result.text, order, result.is_demo),
            reply_markup=main_menu_keyboard(),
        )
    except AIServiceError:
        logger.exception("Не удалось создать ответ на личный вопрос")
        if order is not None:
            await fail_question_order(order.id, "Ошибка AI-сервиса")
        await show_screen(
            progress_message,
            QUESTION_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Непредвиденная ошибка обработки личного вопроса")
        if order is not None:
            await fail_question_order(order.id, "Внутренняя ошибка")
        await show_screen(
            progress_message,
            QUESTION_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.message(QuestionForm.confirm)
async def repeat_question_confirmation(message: Message, state: FSMContext) -> None:
    await show_question_confirmation(message, state)
