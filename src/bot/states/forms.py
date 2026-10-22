from aiogram.fsm.state import State, StatesGroup


class BookingSG(StatesGroup):
    choosing_service = State()
    choosing_slot = State()
    entering_phone = State()
    confirming = State()


class AdminSG(StatesGroup):
    entering_broadcast_text = State()
