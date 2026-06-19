import logging
from datetime import date, time
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.database.models import Order, Profile
from bot.database.repositories import complete_order, create_test_order, fail_order, get_profile
from bot.keyboards.main_menu import NATAL_BUTTON, main_menu_keyboard
from bot.keyboards.natal import (
    NATAL_FOCUSES,
    NATAL_LIFE_STAGES,
    NATAL_SUBFOCUSES,
    NATAL_TIME_ACCURACY,
    NATAL_TIME_PERIODS,
    natal_confirmation_keyboard,
    natal_focus_keyboard,
    natal_hour_keyboard,
    natal_life_stage_keyboard,
    natal_minute_ones_keyboard,
    natal_minute_tens_keyboard,
    natal_needs_profile_keyboard,
    natal_profile_keyboard,
    natal_subfocus_keyboard,
    natal_time_accuracy_keyboard,
    natal_time_period_keyboard,
)
from bot.services.ai import AIServiceError, AstrobotAIService
from bot.services.payments import (
    PaymentServiceError,
    payment_note,
    send_stars_invoice,
    stars_enabled,
)
from bot.services.results import send_order_result
from bot.services.screens import clear_screen, remember_screen, show_screen
from bot.states.natal import NatalChartForm
from bot.texts.ru import (
    NATAL_CONFIRM_TEXT,
    NATAL_ERROR_TEXT,
    NATAL_FOCUS_PROMPT,
    NATAL_GENERATING_TEXT,
    NATAL_HOUR_PROMPT,
    NATAL_LIFE_STAGE_PROMPT,
    NATAL_MINUTE_ONES_PROMPT,
    NATAL_MINUTE_TENS_PROMPT,
    NATAL_NEEDS_PROFILE_TEXT,
    NATAL_REVIEW_TEXT,
    NATAL_SUBFOCUS_PROMPT,
    NATAL_TIME_ACCURACY_PROMPT,
    NATAL_TIME_PERIOD_PROMPT,
    PAYMENT_INVOICE_ERROR_TEXT,
)

logger = logging.getLogger(__name__)
router = Router(name="natal")


def _time_label(value: str | None) -> str:
    return value or "неизвестно"


def _profile_with_time(profile: Profile, birth_time: str | None) -> Profile:
    return Profile(
        name=profile.name,
        birth_date=profile.birth_date,
        birth_time=time.fromisoformat(birth_time) if birth_time else None,
        birth_place=profile.birth_place,
    )


def _natal_input(
    profile: Profile,
    birth_time: str | None,
    time_accuracy: str,
    time_period: str | None,
    life_stage: str,
    focus: str,
    subfocus: str,
) -> dict[str, object]:
    return {
        "profile": {
            "name": profile.name,
            "birth_date": profile.birth_date.isoformat(),
            "birth_time": birth_time,
            "birth_place": profile.birth_place,
        },
        "time_accuracy": time_accuracy,
        "time_period": time_period,
        "life_stage": life_stage,
        "focus": focus,
        "subfocus": subfocus,
    }


async def show_natal_review(
    source: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    profile = await get_profile(telegram_id)
    if profile is None:
        await state.clear()
        await show_screen(
            source,
            NATAL_NEEDS_PROFILE_TEXT,
            reply_markup=natal_needs_profile_keyboard(),
        )
        return

    # Birth time belongs to the natal questionnaire, not the general profile.
    birth_time = None
    await state.set_state(NatalChartForm.review)
    await state.update_data(birth_time=birth_time)
    await show_screen(
        source,
        NATAL_REVIEW_TEXT.format(
            name=escape(profile.name),
            birth_date=profile.birth_date.strftime("%d.%m.%Y"),
            birth_time=_time_label(birth_time),
            birth_place=escape(profile.birth_place or "не указано"),
        ),
        reply_markup=natal_profile_keyboard(),
    )


async def show_natal_focus(source: Message, state: FSMContext) -> None:
    await state.set_state(NatalChartForm.focus)
    await show_screen(source, NATAL_FOCUS_PROMPT, reply_markup=natal_focus_keyboard())


async def show_time_accuracy(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    birth_time = str(data["birth_time"]) if data.get("birth_time") else None
    await state.set_state(NatalChartForm.time_accuracy)
    await show_screen(
        source,
        NATAL_TIME_ACCURACY_PROMPT.format(birth_time=_time_label(birth_time)),
        reply_markup=natal_time_accuracy_keyboard(has_saved_time=birth_time is not None),
    )


async def show_life_stage(source: Message, state: FSMContext) -> None:
    await state.set_state(NatalChartForm.life_stage)
    await show_screen(
        source,
        NATAL_LIFE_STAGE_PROMPT,
        reply_markup=natal_life_stage_keyboard(),
    )


async def show_natal_confirmation(
    source: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    profile = await get_profile(telegram_id)
    if profile is None:
        await show_natal_review(source, state, telegram_id)
        return
    data = await state.get_data()
    focus_key = str(data.get("focus", "full"))
    subfocus_key = str(data.get("subfocus", "balance"))
    birth_time = data.get("birth_time")
    accuracy_key = str(data.get("time_accuracy", "unknown"))
    period_key = str(data.get("time_period", ""))
    life_key = str(data.get("life_stage", "stable"))
    subfocuses = NATAL_SUBFOCUSES.get(focus_key, NATAL_SUBFOCUSES["full"])
    accuracy_label = NATAL_TIME_ACCURACY.get(
        accuracy_key,
        NATAL_TIME_ACCURACY["unknown"],
    )
    period_label = NATAL_TIME_PERIODS.get(period_key)
    if birth_time:
        time_details = f"{birth_time} · {accuracy_label.lower()}"
    elif period_label:
        time_details = period_label
    else:
        time_details = "неизвестно"
    settings = get_settings()
    await state.set_state(NatalChartForm.confirm)
    await show_screen(
        source,
        NATAL_CONFIRM_TEXT.format(
            birth_date=profile.birth_date.strftime("%d.%m.%Y"),
            time_details=escape(time_details),
            birth_place=escape(profile.birth_place or "не указано"),
            life_stage=escape(NATAL_LIFE_STAGES.get(life_key, NATAL_LIFE_STAGES["stable"])),
            focus=escape(NATAL_FOCUSES.get(focus_key, NATAL_FOCUSES["full"])),
            subfocus=escape(subfocuses.get(subfocus_key, next(iter(subfocuses.values())))),
            payment_note=payment_note("natal_chart", settings),
        ),
        reply_markup=natal_confirmation_keyboard(stars_enabled(settings)),
    )


@router.callback_query(F.data == "service:natal")
async def begin_natal_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await state.clear()
        await show_natal_review(callback.message, state, callback.from_user.id)


@router.message(F.text == NATAL_BUTTON)
async def begin_natal_message(message: Message, state: FSMContext) -> None:
    if message.from_user is not None:
        await state.clear()
        await show_natal_review(message, state, message.from_user.id)


@router.callback_query(F.data == "natal:restart")
async def restart_natal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_natal_review(callback.message, state, callback.from_user.id)


@router.callback_query(F.data == "natal:cancel")
async def cancel_natal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "↩️ Натальная карта отменена.",
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(NatalChartForm.review, F.data == "natal:use_profile")
async def use_natal_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_time_accuracy(callback.message, state)


@router.callback_query(F.data == "natal:accuracy_back")
async def natal_accuracy_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_time_accuracy(callback.message, state)


@router.callback_query(
    NatalChartForm.time_accuracy,
    F.data.startswith("natal:accuracy:"),
)
async def select_time_accuracy(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    accuracy = (callback.data or "").rsplit(":", 1)[-1]
    if accuracy not in NATAL_TIME_ACCURACY:
        return
    await state.update_data(time_accuracy=accuracy, time_period=None)
    if not isinstance(callback.message, Message):
        return
    if accuracy == "period":
        await state.set_state(NatalChartForm.time_period)
        await show_screen(
            callback.message,
            NATAL_TIME_PERIOD_PROMPT,
            reply_markup=natal_time_period_keyboard(),
        )
        return
    if accuracy == "unknown":
        await state.update_data(birth_time=None)
        await show_life_stage(callback.message, state)
        return
    data = await state.get_data()
    if data.get("birth_time"):
        await show_life_stage(callback.message, state)
        return
    await state.set_state(NatalChartForm.time_hour)
    await show_screen(
        callback.message,
        NATAL_HOUR_PROMPT,
        reply_markup=natal_hour_keyboard(),
    )


@router.callback_query(NatalChartForm.time_period, F.data.startswith("natal:period:"))
async def select_time_period(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    period = (callback.data or "").rsplit(":", 1)[-1]
    if period not in NATAL_TIME_PERIODS:
        return
    await state.update_data(
        birth_time=None,
        time_accuracy="period",
        time_period=period,
    )
    if isinstance(callback.message, Message):
        await show_life_stage(callback.message, state)


@router.callback_query(F.data == "natal:change_time")
async def change_natal_time(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    if data.get("time_accuracy") not in {"exact", "approximate"}:
        await state.update_data(time_accuracy="exact")
    await state.update_data(time_period=None)
    await state.set_state(NatalChartForm.time_hour)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            NATAL_HOUR_PROMPT,
            reply_markup=natal_hour_keyboard(),
        )


@router.callback_query(NatalChartForm.time_hour, F.data == "natal:time_unknown")
async def natal_time_unknown(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(
        birth_time=None,
        time_accuracy="unknown",
        time_period=None,
    )
    if isinstance(callback.message, Message):
        await show_life_stage(callback.message, state)


@router.callback_query(NatalChartForm.time_hour, F.data.startswith("natal:hour:"))
async def select_natal_hour(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        hour = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    if not 0 <= hour <= 23:
        return
    await state.update_data(time_hour=hour)
    await state.set_state(NatalChartForm.time_minute_tens)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            NATAL_MINUTE_TENS_PROMPT.format(hour=f"{hour:02d}"),
            reply_markup=natal_minute_tens_keyboard(),
        )


@router.callback_query(
    NatalChartForm.time_minute_tens,
    F.data.startswith("natal:minute_tens:"),
)
async def select_natal_minute_tens(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        tens = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    if not 0 <= tens <= 5:
        return
    await state.update_data(time_minute_tens=tens)
    await state.set_state(NatalChartForm.time_minute_ones)
    data = await state.get_data()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            NATAL_MINUTE_ONES_PROMPT.format(
                hour=f"{int(data['time_hour']):02d}",
                tens=tens,
            ),
            reply_markup=natal_minute_ones_keyboard(tens),
        )


@router.callback_query(NatalChartForm.time_minute_ones, F.data == "natal:minute_back")
async def natal_minute_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(NatalChartForm.time_minute_tens)
    data = await state.get_data()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            NATAL_MINUTE_TENS_PROMPT.format(hour=f"{int(data['time_hour']):02d}"),
            reply_markup=natal_minute_tens_keyboard(),
        )


@router.callback_query(
    NatalChartForm.time_minute_ones,
    F.data.startswith("natal:minute_ones:"),
)
async def select_natal_minute_ones(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        ones = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    if not 0 <= ones <= 9:
        return
    data = await state.get_data()
    hour = int(data["time_hour"])
    minute = int(data["time_minute_tens"]) * 10 + ones
    await state.update_data(
        birth_time=f"{hour:02d}:{minute:02d}",
        time_period=None,
    )
    if isinstance(callback.message, Message):
        await show_life_stage(callback.message, state)


@router.callback_query(NatalChartForm.life_stage, F.data.startswith("natal:life:"))
async def select_life_stage(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    life_stage = (callback.data or "").rsplit(":", 1)[-1]
    if life_stage not in NATAL_LIFE_STAGES:
        return
    await state.update_data(life_stage=life_stage)
    if isinstance(callback.message, Message):
        await show_natal_focus(callback.message, state)


@router.callback_query(NatalChartForm.focus, F.data.startswith("natal:focus:"))
async def select_natal_focus(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    focus = (callback.data or "").rsplit(":", 1)[-1]
    if focus not in NATAL_FOCUSES:
        return
    await state.update_data(focus=focus)
    await state.set_state(NatalChartForm.subfocus)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            NATAL_SUBFOCUS_PROMPT.format(focus=escape(NATAL_FOCUSES[focus])),
            reply_markup=natal_subfocus_keyboard(focus),
        )


@router.callback_query(F.data == "natal:focus_back")
async def natal_focus_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_natal_focus(callback.message, state)


@router.callback_query(NatalChartForm.subfocus, F.data.startswith("natal:subfocus:"))
async def select_natal_subfocus(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    subfocus = (callback.data or "").rsplit(":", 1)[-1]
    data = await state.get_data()
    focus = str(data.get("focus", "full"))
    choices = NATAL_SUBFOCUSES.get(focus, NATAL_SUBFOCUSES["full"])
    if subfocus not in choices:
        return
    await state.update_data(subfocus=subfocus)
    if isinstance(callback.message, Message):
        await show_natal_confirmation(callback.message, state, callback.from_user.id)


@router.callback_query(NatalChartForm.confirm, F.data == "natal:confirm")
async def confirm_natal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    profile = await get_profile(callback.from_user.id)
    if profile is None:
        await show_natal_review(callback.message, state, callback.from_user.id)
        return
    data = await state.get_data()
    birth_time = str(data["birth_time"]) if data.get("birth_time") else None
    focus_key = str(data.get("focus", "full"))
    focus = NATAL_FOCUSES.get(focus_key, NATAL_FOCUSES["full"])
    accuracy_key = str(data.get("time_accuracy", "unknown"))
    time_accuracy = NATAL_TIME_ACCURACY.get(
        accuracy_key,
        NATAL_TIME_ACCURACY["unknown"],
    )
    period_key = str(data.get("time_period", ""))
    time_period = NATAL_TIME_PERIODS.get(period_key)
    life_key = str(data.get("life_stage", "stable"))
    life_stage = NATAL_LIFE_STAGES.get(life_key, NATAL_LIFE_STAGES["stable"])
    subfocus_key = str(data.get("subfocus", "balance"))
    subfocuses = NATAL_SUBFOCUSES.get(focus_key, NATAL_SUBFOCUSES["full"])
    subfocus = subfocuses.get(subfocus_key, next(iter(subfocuses.values())))
    input_data = _natal_input(
        profile=profile,
        birth_time=birth_time,
        time_accuracy=time_accuracy,
        time_period=time_period,
        life_stage=life_stage,
        focus=focus,
        subfocus=subfocus,
    )
    settings = get_settings()

    if stars_enabled(settings):
        await state.clear()
        try:
            await send_stars_invoice(
                source=callback.message,
                telegram_id=callback.from_user.id,
                service_code="natal_chart",
                input_data=input_data,
            )
        except PaymentServiceError:
            logger.exception("Не удалось выставить счёт за натальную карту")
            await show_screen(
                callback.message,
                PAYMENT_INVOICE_ERROR_TEXT,
                reply_markup=main_menu_keyboard(),
            )
        return

    await state.clear()
    progress_message = await show_screen(callback.message, NATAL_GENERATING_TEXT)
    order: Order | None = None
    try:
        order = await create_test_order(
            telegram_id=callback.from_user.id,
            service_code="natal_chart",
            price_stars=900,
            input_data=input_data,
            public_id_prefix="N",
        )
        result = await AstrobotAIService(settings).generate_natal_chart(
            profile=_profile_with_time(profile, birth_time),
            focus=focus,
            subfocus=subfocus,
            life_stage=life_stage,
            time_accuracy=time_accuracy,
            time_period=time_period,
            current_date=date.today(),
        )
        await complete_order(
            order_id=order.id,
            result_text=result.text,
            provider=result.provider,
            model=result.model,
        )
        await clear_screen(progress_message)
        last_message = await send_order_result(
            bot=progress_message.bot,
            chat_id=progress_message.chat.id,
            order=order,
            result_text=result.text,
            reply_markup=main_menu_keyboard(),
            is_demo=result.is_demo,
        )
        remember_screen(last_message)
    except AIServiceError:
        logger.exception("Не удалось создать натальную карту")
        if order is not None:
            await fail_order(order.id, "Ошибка AI-сервиса")
        await show_screen(
            progress_message,
            NATAL_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Непредвиденная ошибка натальной карты")
        if order is not None:
            await fail_order(order.id, "Внутренняя ошибка")
        await show_screen(
            progress_message,
            NATAL_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
