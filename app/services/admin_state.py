from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_dataset = State()


class UserStates(StatesGroup):
    waiting_question = State()
    waiting_image = State()
