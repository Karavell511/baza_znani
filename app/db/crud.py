from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset, DatasetChunk, DatasetStatus, DialogLog, User


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None, is_admin: bool) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        if user.username != username:
            user.username = username
        user.is_admin = is_admin
        await session.commit()
        return user

    user = User(telegram_id=telegram_id, username=username, is_admin=is_admin)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_dataset(session: AsyncSession, title: str, description: str | None = None, meta: dict | None = None) -> Dataset:
    dataset = Dataset(title=title, description=description, meta=meta or {})
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)
    return dataset


async def list_datasets(session: AsyncSession, limit: int = 10, offset: int = 0) -> list[Dataset]:
    rows = await session.scalars(select(Dataset).order_by(Dataset.created_at.desc()).limit(limit).offset(offset))
    return list(rows)


async def get_dataset(session: AsyncSession, dataset_id: int) -> Dataset | None:
    return await session.get(Dataset, dataset_id)


async def set_dataset_status(session: AsyncSession, dataset: Dataset, status: DatasetStatus) -> None:
    dataset.status = status
    await session.commit()


async def replace_dataset_chunks(session: AsyncSession, dataset_id: int, chunks: list[str]) -> None:
    await session.execute(delete(DatasetChunk).where(DatasetChunk.dataset_id == dataset_id))
    session.add_all([DatasetChunk(dataset_id=dataset_id, text=chunk, meta={}) for chunk in chunks])
    await session.commit()


async def toggle_dataset_active(session: AsyncSession, dataset_id: int) -> Dataset | None:
    dataset = await session.get(Dataset, dataset_id)
    if not dataset:
        return None
    dataset.is_active = not dataset.is_active
    await session.commit()
    await session.refresh(dataset)
    return dataset


async def delete_dataset(session: AsyncSession, dataset_id: int) -> bool:
    dataset = await session.get(Dataset, dataset_id)
    if not dataset:
        return False
    await session.delete(dataset)
    await session.commit()
    return True


async def get_active_chunks(session: AsyncSession, max_chunks: int) -> list[DatasetChunk]:
    rows = await session.scalars(
        select(DatasetChunk)
        .join(Dataset, Dataset.id == DatasetChunk.dataset_id)
        .where(Dataset.is_active.is_(True), Dataset.status == DatasetStatus.ready)
        .limit(max_chunks)
    )
    return list(rows)


async def create_dialog_log(
    session: AsyncSession,
    user_id: int,
    question: str,
    answer: str | None,
    source_datasets: list[int],
    error: str | None = None,
) -> None:
    session.add(
        DialogLog(
            user_id=user_id,
            question=question,
            answer=answer,
            source_datasets=source_datasets,
            error=error,
        )
    )
    await session.commit()
