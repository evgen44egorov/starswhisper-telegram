from aiogram.fsm.state import State, StatesGroup


class NumerologyForm(StatesGroup):
    period = State()
    confirm = State()
