from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Dataset, DatasetStatus


def chunk_text(content: str, chunk_size: int = 1500) -> list[str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    chunks: list[str] = []
    current = ''
    for line in lines:
        if len(current) + len(line) + 1 <= chunk_size:
            current += f'\n{line}' if current else line
        else:
            chunks.append(current)
            current = line
    if current:
        chunks.append(current)
    return chunks


async def ingest_dataset(session: AsyncSession, dataset: Dataset, text: str) -> int:
    await crud.set_dataset_status(session, dataset, DatasetStatus.processing)
    chunks = chunk_text(text)
    await crud.replace_dataset_chunks(session, dataset.id, chunks)
    await crud.set_dataset_status(session, dataset, DatasetStatus.ready)
    return len(chunks)


async def ingest_dataset_from_file(session: AsyncSession, dataset: Dataset, path: str) -> int:
    try:
        text = Path(path).read_text(encoding='utf-8')
        return await ingest_dataset(session, dataset, text)
    except Exception:
        await crud.set_dataset_status(session, dataset, DatasetStatus.failed)
        raise
