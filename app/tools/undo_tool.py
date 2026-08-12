from sqlalchemy.orm import Session
from app.db.models import Expense, Settlement
from app.db.crud import delete_expense, delete_settlement

def undo_tool(db: Session, group_id: int) -> dict:
    """
    Finds and deletes the most recently added Expense or Settlement in a group.
    """
    # Find latest expense
    latest_expense = db.query(Expense)\
        .filter(Expense.group_id == group_id)\
        .order_by(Expense.id.desc())\
        .first()
        
    # Find latest settlement
    latest_settlement = db.query(Settlement)\
        .filter(Settlement.group_id == group_id)\
        .order_by(Settlement.id.desc())\
        .first()
        
    if not latest_expense and not latest_settlement:
        return {"success": False, "error": "No activities found to undo."}
        
    # Determine which one is more recent by comparing IDs (or created_at)
    # Since IDs auto-increment and we check within the same database session, comparing IDs is extremely reliable
    # We can check which one was created later
    is_expense_latest = False
    
    if latest_expense and not latest_settlement:
        is_expense_latest = True
    elif latest_settlement and not latest_expense:
        is_expense_latest = False
    else:
        # Both exist. Compare created_at timestamps
        if latest_expense.created_at >= latest_settlement.created_at:
            is_expense_latest = True
        else:
            is_expense_latest = False

    if is_expense_latest:
        desc = latest_expense.description or "Expense"
        amt = latest_expense.amount
        delete_expense(db, latest_expense.id)
        return {
            "success": True,
            "action": "delete_expense",
            "message": f"Successfully deleted expense: '{desc}' of {amt} paise."
        }
    else:
        amt = latest_settlement.amount
        delete_settlement(db, latest_settlement.id)
        return {
            "success": True,
            "action": "delete_settlement",
            "message": f"Successfully deleted settlement of {amt} paise."
        }
