from __future__ import annotations

import asyncio

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject

from app.bot.handlers import admin, common, user
from app.bot.middlewares.rate_limit import UserMessageRateLimitMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal, init_db
from app.db.crud import get_or_create_user
from app.llm.client import llm_client


class AppContextMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with SessionLocal() as session:
            data['session'] = session
            data['llm_client'] = llm_client
            if data.get('event_from_user'):
                u = data['event_from_user']
                settings = get_settings()
                tg_user = await get_or_create_user(
                    session,
                    telegram_id=u.id,
                    username=u.username,
                    is_admin=u.id in settings.admin_id_set,
                )
                data['tg_user'] = tg_user
            return await handler(event, data)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.update.middleware(AppContextMiddleware())
    dp.message.middleware(UserMessageRateLimitMiddleware())

    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
