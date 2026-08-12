from sqlalchemy.orm import Session
from app.db.models import Debt

def query_balance_tool(db: Session, group_id: int) -> dict:
    """
    Queries and returns the optimized debts of a group, resolving user IDs to names.
    """
    debts = db.query(Debt).filter(Debt.group_id == group_id).all()
    
    if not debts:
        return {
            "success": True,
            "debts": [],
            "message": "All settled up! No active debts."
        }
        
    formatted_debts = []
    for debt in debts:
        formatted_debts.append({
            "debtor_id": debt.debtor_id,
            "debtor_name": debt.debtor.name or f"User {debt.debtor_id}",
            "creditor_id": debt.creditor_id,
            "creditor_name": debt.creditor.name or f"User {debt.creditor_id}",
            "amount": debt.amount  # in paise
        })
        
    return {
        "success": True,
        "debts": formatted_debts
    }
