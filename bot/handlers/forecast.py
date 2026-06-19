import logging
from datetime import date
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.database.repositories import (
    get_cached_daily_forecast,
    get_profile,
    save_daily_forecast,
)
from bot.keyboards.forecast import (
    forecast_confirmation_keyboard,
    forecast_needs_profile_keyboard,
)
from bot.keyboards.main_menu import FORECAST_BUTTON, main_menu_keyboard
from bot.services.ai import AIServiceError, AstrobotAIService
from bot.services.screens import show_screen
from bot.texts.ru import (
    FORECAST_CONSENT_DEMO_TEXT,
    FORECAST_CONSENT_OPENAI_TEXT,
    FORECAST_ERROR_TEXT,
    FORECAST_GENERATING_TEXT,
    FORECAST_NEEDS_PROFILE_TEXT,
)
from bot.utils.telegram import escape_and_limit

logger = logging.getLogger(__name__)
router = Router(name="forecast")


async def prepare_forecast(source: Message, telegram_id: int) -> None:
    profile = await get_profile(telegram_id)
    if profile is None:
        await show_screen(
            source,
            FORECAST_NEEDS_PROFILE_TEXT,
            reply_markup=forecast_needs_profile_keyboard(),
        )
        return

    settings = get_settings()
    consent_text = (
        FORECAST_CONSENT_DEMO_TEXT
        if settings.ai_provider.strip().lower() == "demo"
        else FORECAST_CONSENT_OPENAI_TEXT
    )
    await show_screen(
        source,
        consent_text.format(name=escape(profile.name)),
        reply_markup=forecast_confirmation_keyboard(),
    )


def format_forecast_result(text: str, is_demo: bool) -> str:
    return (
        f"{escape_and_limit(text)}\n\n"
        "<i>Прогноз носит развлекательный и саморефлексивный характер.</i>"
    )


@router.callback_query(F.data.in_({"start:forecast", "service:forecast"}))
async def prepare_forecast_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await prepare_forecast(callback.message, callback.from_user.id)


@router.message(F.text == FORECAST_BUTTON)
async def prepare_forecast_message(message: Message) -> None:
    if message.from_user is not None:
        await prepare_forecast(message, message.from_user.id)


@router.callback_query(F.data == "forecast:generate")
async def generate_forecast_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    profile = await get_profile(callback.from_user.id)
    if profile is None:
        await prepare_forecast(callback.message, callback.from_user.id)
        return

    current_date = date.today()
    settings = get_settings()
    cached = await get_cached_daily_forecast(callback.from_user.id, current_date)
    expected_provider = settings.ai_provider.strip().lower()
    cache_matches_settings = cached is not None and cached.provider == expected_provider
    if expected_provider == "openai" and cached is not None:
        cache_matches_settings = (
            cache_matches_settings and cached.model == settings.ai_model
        )

    if cached is not None and cache_matches_settings:
        await show_screen(
            callback.message,
            format_forecast_result(cached.result_text, cached.is_demo),
            reply_markup=main_menu_keyboard(),
        )
        return

    progress_message = await show_screen(
        callback.message,
        FORECAST_GENERATING_TEXT,
    )
    try:
        result = await AstrobotAIService(settings).generate_daily_forecast(
            profile,
            current_date,
        )
        await save_daily_forecast(
            telegram_id=callback.from_user.id,
            generation_date=current_date,
            result_text=result.text,
            provider=result.provider,
            model=result.model,
            prompt_version=result.prompt_version,
            is_demo=result.is_demo,
        )
        await show_screen(
            progress_message,
            format_forecast_result(result.text, result.is_demo),
            reply_markup=main_menu_keyboard(),
        )
    except AIServiceError:
        logger.exception("Не удалось создать дневной прогноз")
        await show_screen(
            progress_message,
            FORECAST_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Непредвиденная ошибка при создании дневного прогноза")
        await show_screen(
            progress_message,
            FORECAST_ERROR_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "forecast:cancel")
async def cancel_forecast_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            "✨ Что хочешь узнать сейчас?",
            reply_markup=main_menu_keyboard(),
        )
