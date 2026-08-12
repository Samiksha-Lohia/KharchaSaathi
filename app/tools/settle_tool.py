from sqlalchemy.orm import Session
from app.db.crud import create_settlement

def settle_tool(
    db: Session,
    group_id: int,
    payer_id: int,
    payee_id: int,
    amount: int  # in paise
) -> dict:
    """
    Business logic wrapper for recording settlements between two users.
    """
    try:
        settlement = create_settlement(
            db=db,
            group_id=group_id,
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount
        )
        return {
            "success": True,
            "settlement_id": settlement.id,
            "payer_id": payer_id,
            "payee_id": payee_id,
            "amount": amount
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
