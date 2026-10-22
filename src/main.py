import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from src.config import settings
from src.db.session import async_session_factory, init_db
from src.db.repositories import seed_demo_data
from src.bot.middlewares.auth_db import DatabaseAndRBACMiddleware
from src.bot.handlers.client import client_router
from src.bot.handlers.admin import admin_router
from src.services.notification_service import scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Initializing database and demo seed...")

    await init_db()
    async with async_session_factory() as session:
        await seed_demo_data(session)

    storage = RedisStorage.from_url(settings.redis_url)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DatabaseAndRBACMiddleware())
    dp.include_router(admin_router)
    dp.include_router(client_router)

    scheduler.start()
    logger.info("Starting Service CRM Bot polling...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
