from pydantic import BaseModel


class CreateTransactionRequest(BaseModel):
    user_id: int
    amount: float
    currency: str = "USDT"
    payment_method: str
    type: str = "purchase"  # or "renewal"


class UpdateTransactionStatusRequest(BaseModel):
    transaction_id: int
    status: str
    external_tx_id: str | None = None
    comment: str | None = None
