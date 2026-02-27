from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='Загрузить чат', callback_data='admin:upload')
    kb.button(text='Список датасетов', callback_data='admin:list')
    kb.button(text='Анализ и обучение', callback_data='admin:train')
    kb.button(text='Настройки LLM', callback_data='admin:settings')
    kb.button(text='Статус LLM', callback_data='admin:status')
    kb.adjust(1)
    return kb.as_markup()


def dataset_actions_keyboard(dataset_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='Запустить анализ', callback_data=f'admin:analyze:{dataset_id}')
    kb.button(text='Вкл/Выкл в контексте', callback_data=f'admin:toggle:{dataset_id}')
    kb.button(text='Удалить', callback_data=f'admin:delete:{dataset_id}')
    kb.adjust(1)
    return kb.as_markup()
