from aiogram.fsm.state import State, StatesGroup


class NatalChartForm(StatesGroup):
    review = State()
    time_accuracy = State()
    time_hour = State()
    time_minute_tens = State()
    time_minute_ones = State()
    time_period = State()
    life_stage = State()
    focus = State()
    subfocus = State()
    confirm = State()
