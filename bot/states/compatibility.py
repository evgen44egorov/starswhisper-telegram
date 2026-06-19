from aiogram.fsm.state import State, StatesGroup


class CompatibilityForm(StatesGroup):
    relationship_type = State()
    partner_name = State()
    partner_birth_date = State()
    partner_birth_time = State()
    partner_birth_place = State()
    confirm = State()

