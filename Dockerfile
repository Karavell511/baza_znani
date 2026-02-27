FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV BOT_TOKEN='' \
    ADMIN_IDS='' \
    DB_URL='sqlite+aiosqlite:///./bot.db' \
    GPT4FREE_PROVIDER_TEXT='Liaobots' \
    GPT4FREE_PROVIDER_VISION='PollinationsAI' \
    LLM_MAX_RETRIES='5' \
    LLM_BACKOFF_BASE='1' \
    LLM_GLOBAL_RPS='1' \
    LLM_USER_RPS='0.5' \
    CONTEXT_MAX_CHUNKS='5' \
    LOG_LEVEL='INFO'

CMD ["python", "-m", "app.bot.main"]
