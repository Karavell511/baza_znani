from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class UserMessageRateLimitMiddleware(BaseMiddleware):
    def __init__(self, max_per_minute: int = 20) -> None:
        self.max_per_minute = max_per_minute
        self.history: dict[int, Deque[float]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            now = time.time()
            q = self.history[event.from_user.id]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.max_per_minute:
                await event.answer('Слишком много сообщений за минуту. Подождите немного.')
                return None
            q.append(now)
        return await handler(event, data)
