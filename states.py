from aiogram.fsm.state import State, StatesGroup

class AddReminderState(StatesGroup):
    choosing_category = State()
    waiting_for_text = State()
