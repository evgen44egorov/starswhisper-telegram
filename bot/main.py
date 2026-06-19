import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from pydantic import ValidationError

from bot.config import get_settings
from bot.database.session import close_database, configure_database, init_database
from bot.handlers.admin import router as admin_router
from bot.handlers.compatibility import router as compatibility_router
from bot.handlers.forecast import router as forecast_router
from bot.handlers.menu import router as menu_router
from bot.handlers.monthly import router as monthly_router
from bot.handlers.natal import router as natal_router
from bot.handlers.orders import router as orders_router
from bot.handlers.payments import router as payments_router
from bot.handlers.profile import router as profile_router
from bot.handlers.question import router as question_router
from bot.handlers.start import router as start_router
from bot.handlers.support import router as support_router
from bot.handlers.tarot import router as tarot_router
from bot.services.payments import PaymentServiceError, validate_payments_configuration
from bot.services.recovery import recover_paid_orders


async def main() -> None:
    settings = get_settings()
    validate_payments_configuration(settings)
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    configure_database(settings.database_url)
    await init_database()
    await recover_paid_orders(bot)

    dispatcher = Dispatcher()
    dispatcher.include_router(admin_router)
    dispatcher.include_router(start_router)
    dispatcher.include_router(profile_router)
    dispatcher.include_router(forecast_router)
    dispatcher.include_router(question_router)
    dispatcher.include_router(compatibility_router)
    dispatcher.include_router(monthly_router)
    dispatcher.include_router(natal_router)
    dispatcher.include_router(tarot_router)
    dispatcher.include_router(payments_router)
    dispatcher.include_router(orders_router)
    dispatcher.include_router(support_router)
    dispatcher.include_router(menu_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.getLogger(__name__).info("Astrobot запущен в режиме %s", settings.bot_env)
    try:
        await dispatcher.start_polling(bot, close_bot_session=False)
    finally:
        await close_database()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValidationError:
        raise SystemExit(
            "Не заполнен BOT_TOKEN. Откройте файл .env и вставьте токен от BotFather."
        ) from None
    except PaymentServiceError as error:
        raise SystemExit(str(error)) from None
