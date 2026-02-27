from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.user import main_user_keyboard

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message) -> None:
    await message.answer('Привет! Выбери действие:', reply_markup=main_user_keyboard())
