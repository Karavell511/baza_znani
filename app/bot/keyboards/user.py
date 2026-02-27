from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_user_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='Задать вопрос', callback_data='user:ask')
    kb.button(text='Отправить картинку', callback_data='user:image')
    kb.button(text='Помощь', callback_data='user:help')
    kb.adjust(1)
    return kb.as_markup()


def response_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='Спросить ещё', callback_data='user:ask')
    kb.button(text='Удалить диалог', callback_data='user:delete_dialog')
    kb.adjust(1)
    return kb.as_markup()
