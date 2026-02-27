from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import admin_menu_keyboard, dataset_actions_keyboard
from app.db import crud
from app.db.models import DatasetStatus
from app.services.admin_state import AdminStates
from app.services.ingest import ingest_dataset

router = Router()


@router.message(Command('admin'))
async def admin_menu(message: Message, tg_user) -> None:
    if not tg_user.is_admin:
        await message.answer('Недостаточно прав.')
        return
    await message.answer('Админ-панель:', reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == 'admin:upload')
async def admin_upload(callback: CallbackQuery, state, tg_user) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    await state.set_state(AdminStates.waiting_dataset)
    await callback.message.answer('Пришлите файл с чатом (txt/json/html) или текст.')
    await callback.answer()


@router.message(AdminStates.waiting_dataset)
async def receive_dataset(message: Message, session: AsyncSession, state, tg_user, bot) -> None:
    if not tg_user.is_admin:
        await message.answer('Недостаточно прав.')
        return

    text = message.text or ''
    title = f'dataset_{message.message_id}'
    if message.document:
        file = await bot.get_file(message.document.file_id)
        content = await bot.download_file(file.file_path)
        data = content.read().decode('utf-8', errors='ignore')
        title = message.document.file_name or title
    else:
        data = text

    dataset = await crud.create_dataset(session, title=title, meta={'source': 'telegram'})
    await message.answer(
        f'Датасет #{dataset.id} создан (pending). Запускаю анализ...',
        reply_markup=dataset_actions_keyboard(dataset.id),
    )
    try:
        chunks_count = await ingest_dataset(session, dataset, data)
        await message.answer(f'Готово: {chunks_count} chunks, статус ready.')
    except Exception as exc:
        await crud.set_dataset_status(session, dataset, DatasetStatus.failed)
        await message.answer(f'Ошибка обучения: {exc}')
    await state.clear()


@router.callback_query(F.data == 'admin:list')
async def admin_list(callback: CallbackQuery, session: AsyncSession, tg_user) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    datasets = await crud.list_datasets(session, limit=10, offset=0)
    if not datasets:
        await callback.message.answer('Датасетов пока нет.')
    for ds in datasets:
        await callback.message.answer(
            f'#{ds.id} {ds.title}\nstatus={ds.status.value} active={ds.is_active}',
            reply_markup=dataset_actions_keyboard(ds.id),
        )
    await callback.answer()


@router.callback_query(F.data == 'admin:train')
async def admin_train(callback: CallbackQuery) -> None:
    await callback.message.answer('Используйте кнопки "Запустить анализ" у датасета в списке.')
    await callback.answer()


@router.callback_query(F.data == 'admin:settings')
async def admin_settings(callback: CallbackQuery, tg_user) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    await callback.message.answer('Настройки LLM пока через ENV: provider, retries, rps, context max chunks.')
    await callback.answer()


@router.callback_query(F.data == 'admin:status')
async def admin_status(callback: CallbackQuery, tg_user, llm_client) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    st = llm_client.get_status()
    await callback.message.answer(
        'LLM статус:\n'
        f'✅ success: {st.success_last_min}/мин, {st.success_last_hour}/час\n'
        f'❌ errors: {st.errors_last_min}/мин, {st.errors_last_hour}/час\n'
        f'⛔ rate limit: {st.ratelimit_last_min}/мин, {st.ratelimit_last_hour}/час\n'
        f'Cooldowns: {st.cooldowns or {}}'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('admin:toggle:'))
async def toggle_dataset(callback: CallbackQuery, session: AsyncSession, tg_user) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    dataset_id = int(callback.data.split(':')[-1])
    ds = await crud.toggle_dataset_active(session, dataset_id)
    await callback.message.answer(f'Датасет #{dataset_id} active={ds.is_active}' if ds else 'Датасет не найден')
    await callback.answer()


@router.callback_query(F.data.startswith('admin:delete:'))
async def delete_dataset(callback: CallbackQuery, session: AsyncSession, tg_user) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    dataset_id = int(callback.data.split(':')[-1])
    ok = await crud.delete_dataset(session, dataset_id)
    await callback.message.answer('Удалено' if ok else 'Датасет не найден')
    await callback.answer()


@router.callback_query(F.data.startswith('admin:analyze:'))
async def analyze_dataset(callback: CallbackQuery, session: AsyncSession, tg_user) -> None:
    if not tg_user.is_admin:
        await callback.answer('Нет прав', show_alert=True)
        return
    dataset_id = int(callback.data.split(':')[-1])
    ds = await crud.get_dataset(session, dataset_id)
    if not ds:
        await callback.message.answer('Датасет не найден')
        await callback.answer()
        return
    await callback.message.answer('Повторный анализ работает при новой загрузке контента в MVP.')
    await callback.answer()
