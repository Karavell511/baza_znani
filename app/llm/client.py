from __future__ import annotations

import asyncio
import logging
import random
import time
import base64
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from g4f.client import AsyncClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FRIENDLY_OVERLOADED = 'Извини, сейчас модель перегружена, попробуй позже.'
FRIENDLY_RATE_LIMIT = 'Слишком много запросов, попробуйте чуть позже.'


@dataclass
class LLMStats:
    success_last_min: int = 0
    success_last_hour: int = 0
    errors_last_min: int = 0
    errors_last_hour: int = 0
    ratelimit_last_min: int = 0
    ratelimit_last_hour: int = 0
    cooldowns: dict[str, float] | None = None


class SlidingCounter:
    def __init__(self) -> None:
        self.success: deque[float] = deque()
        self.errors: deque[float] = deque()
        self.ratelimits: deque[float] = deque()

    def _trim(self) -> None:
        now = time.time()
        for q in (self.success, self.errors, self.ratelimits):
            while q and now - q[0] > 3600:
                q.popleft()

    def add_success(self) -> None:
        self.success.append(time.time())
        self._trim()

    def add_error(self) -> None:
        self.errors.append(time.time())
        self._trim()

    def add_ratelimit(self) -> None:
        self.ratelimits.append(time.time())
        self._trim()

    def counts(self) -> LLMStats:
        self._trim()
        now = time.time()
        minute = lambda q: sum(1 for t in q if now - t <= 60)
        return LLMStats(
            success_last_min=minute(self.success),
            success_last_hour=len(self.success),
            errors_last_min=minute(self.errors),
            errors_last_hour=len(self.errors),
            ratelimit_last_min=minute(self.ratelimits),
            ratelimit_last_hour=len(self.ratelimits),
        )


class InMemoryThrottler:
    def __init__(self, global_rps: float, user_rps: float):
        self.global_interval = 1 / global_rps if global_rps > 0 else 0
        self.user_interval = 1 / user_rps if user_rps > 0 else 0
        self.global_last = 0.0
        self.user_last: dict[int, float] = {}
        self.lock = asyncio.Lock()

    async def acquire(self, user_id: int | None) -> None:
        async with self.lock:
            now = time.time()
            wait_for = 0.0
            if self.global_interval:
                wait_for = max(wait_for, (self.global_last + self.global_interval) - now)
            if user_id is not None and self.user_interval:
                last = self.user_last.get(user_id, 0.0)
                wait_for = max(wait_for, (last + self.user_interval) - now)

        if wait_for > 0:
            if wait_for > 5:
                raise RuntimeError(FRIENDLY_RATE_LIMIT)
            await asyncio.sleep(wait_for)

        async with self.lock:
            ts = time.time()
            self.global_last = ts
            if user_id is not None:
                self.user_last[user_id] = ts


class G4FClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncClient()
        self.throttler = InMemoryThrottler(self.settings.llm_global_rps, self.settings.llm_user_rps)
        self.stats = SlidingCounter()
        self.provider_errors = defaultdict(int)
        self.provider_cooldowns: dict[str, float] = {}

    def _providers_for_mode(self, vision: bool) -> list[str]:
        primary = self.settings.gpt4free_provider_vision if vision else self.settings.gpt4free_provider_text
        fallback = self.settings.gpt4free_fallback_vision if vision else self.settings.gpt4free_fallback_text
        result = [primary]
        if fallback:
            result.append(fallback)
        return result

    def _is_cooldown(self, provider: str) -> bool:
        return self.provider_cooldowns.get(provider, 0) > time.time()

    def _mark_failure(self, provider: str, is_ratelimit: bool = False) -> None:
        self.provider_errors[provider] += 1
        self.stats.add_ratelimit() if is_ratelimit else self.stats.add_error()
        if self.provider_errors[provider] >= 3:
            self.provider_cooldowns[provider] = time.time() + self.settings.llm_provider_cooldown_s

    def _mark_success(self, provider: str) -> None:
        self.provider_errors[provider] = 0
        self.stats.add_success()

    async def _call_with_retry(self, *, messages: list[dict[str, Any]], user_id: int | None, vision: bool) -> str:
        await self.throttler.acquire(user_id)
        providers = self._providers_for_mode(vision)

        for attempt in range(1, self.settings.llm_max_retries + 1):
            for provider in providers:
                if self._is_cooldown(provider):
                    continue
                try:
                    response = await self.client.chat.completions.create(
                        model=provider,
                        messages=messages,
                    )
                    text = response.choices[0].message.content
                    self._mark_success(provider)
                    return text
                except Exception as exc:
                    msg = str(exc).lower()
                    is_rl = 'rate' in msg or '429' in msg or 'limit' in msg
                    self._mark_failure(provider, is_rl)
                    logger.warning('llm_fail provider=%s attempt=%s/%s reason=%s', provider, attempt, self.settings.llm_max_retries, exc)

            sleep_time = self.settings.llm_backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            await asyncio.sleep(sleep_time)

        raise RuntimeError(FRIENDLY_OVERLOADED)

    async def ask_text(self, prompt: str, system: str | None, *, user_id: int | None = None) -> str:
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        try:
            return await self._call_with_retry(messages=messages, user_id=user_id, vision=False)
        except Exception as exc:
            logger.exception('ask_text failed: %s', exc)
            if str(exc) in (FRIENDLY_OVERLOADED, FRIENDLY_RATE_LIMIT):
                return str(exc)
            return FRIENDLY_OVERLOADED

    async def ask_vision(self, prompt: str, image_bytes: bytes, *, user_id: int | None = None) -> str:
        encoded = base64.b64encode(image_bytes).decode('utf-8')
        messages = [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{encoded}'}},
                ],
            }
        ]
        try:
            return await self._call_with_retry(messages=messages, user_id=user_id, vision=True)
        except Exception as exc:
            logger.exception('ask_vision failed: %s', exc)
            if str(exc) in (FRIENDLY_OVERLOADED, FRIENDLY_RATE_LIMIT):
                return str(exc)
            return FRIENDLY_OVERLOADED

    def get_status(self) -> LLMStats:
        stats = self.stats.counts()
        stats.cooldowns = {
            k: max(0.0, v - time.time())
            for k, v in self.provider_cooldowns.items()
            if v > time.time()
        }
        return stats


llm_client = G4FClient()
