from aiogram.fsm.state import State, StatesGroup


class TarotForm(StatesGroup):
    spread = State()
    area = State()
    question = State()
    confirm = State()
