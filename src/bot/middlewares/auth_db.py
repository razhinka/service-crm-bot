from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser

from src.config import settings
from src.db.repositories import UserRepository
from src.db.session import async_session_factory


class DatabaseAndRBACMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")

        async with async_session_factory() as session:
            data["session"] = session

            if tg_user is not None and not tg_user.is_bot:
                user_repo = UserRepository(session)
                is_admin = tg_user.id in settings.admin_ids
                db_user = await user_repo.get_or_create_user(
                    tg_id=tg_user.id,
                    full_name=tg_user.full_name,
                    username=tg_user.username,
                    is_admin=is_admin,
                )
                data["user"] = db_user

            return await handler(event, data)
