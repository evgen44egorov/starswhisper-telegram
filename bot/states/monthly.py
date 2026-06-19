from aiogram.fsm.state import State, StatesGroup


class MonthlyForecastForm(StatesGroup):
    period = State()
    area = State()
    confirm = State()

