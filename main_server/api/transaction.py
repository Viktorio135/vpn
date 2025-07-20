import logging

from fastapi import APIRouter, Depends


from schemas.transaction import CreateTransactionRequest, UpdateTransactionStatusRequest
from database.repository import TransactionRepository
from dependencies import get_transaction_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/create/")
async def create_transaction(
    data: CreateTransactionRequest,
    transaction_repo: TransactionRepository = Depends(get_transaction_repo)
):
    """
    Create a new transaction.
    """
    transaction = transaction_repo.create(
        user_id=data.user_id,
        amount=data.amount,
        currency=data.currency,
        type=data.type,
        payment_method=data.payment_method
    )

    if not transaction:
        logger.error("Failed to create transaction")
        return {"error": "Failed to create transaction"}

    return {
        "id": transaction.id,
        "status": transaction.status,
        "created_at": transaction.created_at.isoformat(),
        "external_tx_id": transaction.external_tx_id
    }


@router.post("/update_status/")
async def update_transaction_status(
    data: UpdateTransactionStatusRequest,
    transaction_repo: TransactionRepository = Depends(get_transaction_repo)
):
    transaction = transaction_repo.change_transaction_status(
        transaction_id=data.transaction_id,
        status=data.status,
        external_tx_id=data.external_tx_id,
        comment=data.comment
    )
    if not transaction:
        logger.error(f"Transaction not found: {data.transaction_id}")
        return {"error": "Transaction not found"}
    return {
        "id": transaction.id,
        "status": transaction.status,
        "external_tx_id": transaction.external_tx_id,
        "comment": transaction.comment,
        "created_at": transaction.created_at.isoformat()
    }
