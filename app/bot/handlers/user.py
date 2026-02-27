from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import response_keyboard
from app.db import crud
from app.llm.rag import answer_with_context
from app.services.admin_state import UserStates

router = Router()


@router.callback_query(F.data == 'user:ask')
async def ask_btn(callback: CallbackQuery, state) -> None:
    await state.set_state(UserStates.waiting_question)
    await callback.message.answer('Напишите ваш вопрос текстом.')
    await callback.answer()


@router.callback_query(F.data == 'user:image')
async def image_btn(callback: CallbackQuery, state) -> None:
    await state.set_state(UserStates.waiting_image)
    await callback.message.answer('Пришлите фото или изображение документом.')
    await callback.answer()


@router.callback_query(F.data == 'user:help')
async def help_btn(callback: CallbackQuery) -> None:
    await callback.message.answer('Используйте кнопки: вопрос или картинка. Админу доступна команда /admin.')
    await callback.answer()


@router.message(UserStates.waiting_question, F.text)
async def handle_question(message: Message, state, session: AsyncSession, tg_user) -> None:
    answer, ds = await answer_with_context(session, message.text, user_id=message.from_user.id)
    await crud.create_dialog_log(session, tg_user.id, message.text, answer, ds)
    await state.clear()
    await message.answer(answer, reply_markup=response_keyboard())


@router.message(UserStates.waiting_image, F.photo | F.document)
async def handle_image(message: Message, state, session: AsyncSession, tg_user, bot, llm_client) -> None:
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    file = await bot.get_file(file_id)
    content = await bot.download_file(file.file_path)
    image_bytes = content.read()
    prompt = 'Проанализируй изображение и кратко опиши его.'
    answer = await llm_client.ask_vision(prompt=prompt, image_bytes=image_bytes, user_id=message.from_user.id)
    await crud.create_dialog_log(session, tg_user.id, '[image]', answer, [])
    await state.clear()
    await message.answer(answer, reply_markup=response_keyboard())
