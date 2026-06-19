from aiogram.fsm.state import State, StatesGroup


class ProfileForm(StatesGroup):
    name = State()
    birth_date = State()
    birth_time = State()
    birth_place = State()
    confirm = State()

