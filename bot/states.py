from aiogram.fsm.state import State, StatesGroup


class PaymentState(StatesGroup):
    start_time = State()
    CHOOSE_METHOD = State()
    transaction_id = State()
    AWAITING_WALLET = State()
    AWAITING_PAYMENT = State()


class RenewState(StatesGroup):
    CHOOSE_PERIOD = State()
    CHOOSE_METHOD = State()
    transaction_id = State()
    AWAITING_WALLET = State()
    AWAITING_PAYMENT = State()