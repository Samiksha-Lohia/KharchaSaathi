from sqlalchemy.orm import Session
from app.db.crud import create_expense, get_group_members
from app.db.models import Expense

def add_expense_tool(
    db: Session,
    group_id: int,
    paid_by_id: int,
    amount: int,  # in paise
    description: str | None,
    split_member_ids: list[int] | None = None
) -> dict:
    """
    Business logic wrapper for adding group expenses.
    Distributes splits equally among the group members, handling division remainders in integer paise.
    """
    # 1. Fetch group members to calculate splits
    members = get_group_members(db, group_id)
    if not members:
        return {"success": False, "error": "No members in group"}

    member_ids = [m.user_id for m in members]
    
    # If specific split participants are requested, check validity and use them
    if split_member_ids:
        # Filter to make sure they are members of the group
        target_members = [uid for uid in split_member_ids if uid in member_ids]
        if not target_members:
            return {"success": False, "error": "None of the specified split participants are group members"}
    else:
        # Default: split equally among all members
        target_members = member_ids

    # 2. Distribute amount, handling division remainders
    n = len(target_members)
    base_split = amount // n
    remainder = amount % n
    
    splits = []
    for i, user_id in enumerate(target_members):
        # Greedily allocate 1 extra paise of the remainder to the first few users
        extra = 1 if i < remainder else 0
        splits.append({
            "user_id": user_id,
            "amount": base_split + extra
        })
        
    # 3. Create expense and splits in db
    expense = create_expense(
        db=db,
        group_id=group_id,
        paid_by=paid_by_id,
        amount=amount,
        description=description,
        splits=splits
    )
    
    return {
        "success": True,
        "expense_id": expense.id,
        "amount": expense.amount,
        "description": expense.description,
        "splits_count": len(splits)
    }
