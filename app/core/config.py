from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    bot_token: str = Field(alias='BOT_TOKEN')
    admin_ids: str = Field(default='', alias='ADMIN_IDS')
    db_url: str = Field(default='sqlite+aiosqlite:///./bot.db', alias='DB_URL')

    gpt4free_provider_text: str = Field(default='Liaobots', alias='GPT4FREE_PROVIDER_TEXT')
    gpt4free_provider_vision: str = Field(default='PollinationsAI', alias='GPT4FREE_PROVIDER_VISION')
    gpt4free_fallback_text: str | None = Field(default=None, alias='GPT4FREE_FALLBACK_PROVIDER_TEXT')
    gpt4free_fallback_vision: str | None = Field(default=None, alias='GPT4FREE_FALLBACK_PROVIDER_VISION')

    llm_max_retries: int = Field(default=5, alias='LLM_MAX_RETRIES')
    llm_backoff_base: float = Field(default=1.0, alias='LLM_BACKOFF_BASE')
    llm_global_rps: float = Field(default=1.0, alias='LLM_GLOBAL_RPS')
    llm_user_rps: float = Field(default=0.5, alias='LLM_USER_RPS')
    llm_provider_cooldown_s: int = Field(default=120, alias='LLM_PROVIDER_COOLDOWN_S')

    context_max_chunks: int = Field(default=5, alias='CONTEXT_MAX_CHUNKS')
    context_max_chars: int = Field(default=10_000, alias='CONTEXT_MAX_CHARS')
    response_mode: Literal['brief', 'detailed'] = Field(default='brief', alias='RESPONSE_MODE')

    log_level: str = Field(default='INFO', alias='LOG_LEVEL')

    @property
    def admin_id_set(self) -> set[int]:
        return {int(i.strip()) for i in self.admin_ids.split(',') if i.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
