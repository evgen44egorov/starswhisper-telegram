from aiogram.fsm.state import State, StatesGroup


class QuestionForm(StatesGroup):
    area = State()
    text = State()
    confirm = State()

