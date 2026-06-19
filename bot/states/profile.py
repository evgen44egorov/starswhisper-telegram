from aiogram.fsm.state import State, StatesGroup


class ProfileForm(StatesGroup):
    name = State()
    birth_year = State()
    birth_month = State()
    birth_day = State()
    birth_place = State()
    confirm = State()
