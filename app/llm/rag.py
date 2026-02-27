from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.crud import get_active_chunks
from app.llm.client import llm_client


async def answer_with_context(session: AsyncSession, question: str, *, user_id: int | None = None) -> tuple[str, list[int]]:
    settings = get_settings()
    chunks = await get_active_chunks(session, settings.context_max_chunks)

    context_parts: list[str] = []
    dataset_ids: list[int] = []
    total = 0

    for ch in chunks:
        if total >= settings.context_max_chars:
            break
        piece = f'[Dataset #{ch.dataset_id}]\n{ch.text}\n'
        total += len(piece)
        context_parts.append(piece)
        if ch.dataset_id not in dataset_ids:
            dataset_ids.append(ch.dataset_id)

    context = '\n'.join(context_parts)
    response_style = 'Кратко и по делу.' if settings.response_mode == 'brief' else 'Подробно с пояснениями.'
    system = (
        'Ты ассистент, отвечающий только на основе контекста. '
        'Если информации не хватает — честно скажи, что не знаешь. '
        f'Формат ответа: {response_style}'
    )

    if not context:
        system += ' База знаний пуста, скажи об этом и дай общий ответ если можешь.'

    prompt = f'Контекст:\n{context or "<пусто>"}\n\nВопрос пользователя: {question}'
    answer = await llm_client.ask_text(prompt=prompt, system=system, user_id=user_id)
    return answer, dataset_ids
