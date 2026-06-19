from aiogram.fsm.state import State, StatesGroup


class CompatibilityForm(StatesGroup):
    relationship_type = State()
    partner_name = State()
    partner_birth_year = State()
    partner_birth_month = State()
    partner_birth_day = State()
    partner_birth_time = State()
    partner_birth_place = State()
    confirm = State()
