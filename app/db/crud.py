from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.db.models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement, Debt
from app.algorithms.debt_optimizer import optimize_debts
import logging

logger = logging.getLogger(__name__)

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_phone(db: Session, phone_number: str) -> User | None:
    return db.query(User).filter(User.phone_number == phone_number).first()

def create_user(db: Session, phone_number: str, name: str | None = None) -> User:
    try:
        user = User(phone_number=phone_number, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user {phone_number}: {e}")
        raise

# --- Group CRUD ---
def get_group(db: Session, group_id: int) -> Group | None:
    return db.query(Group).filter(Group.id == group_id).first()

def create_group(db: Session, name: str) -> Group:
    try:
        group = Group(name=name)
        db.add(group)
        db.commit()
        db.refresh(group)
        return group
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating group {name}: {e}")
        raise

def add_user_to_group(db: Session, group_id: int, user_id: int, role: str = "member") -> GroupMember:
    try:
        member = GroupMember(group_id=group_id, user_id=user_id, role=role)
        db.add(member)
        db.commit()
        db.refresh(member)
        return member
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding user {user_id} to group {group_id}: {e}")
        raise

def get_group_members(db: Session, group_id: int) -> list[GroupMember]:
    return db.query(GroupMember).filter(GroupMember.group_id == group_id).all()

# --- Debt Recomputation Hook ---
def recompute_debts(db: Session, group_id: int):
    """
    Derived/Cached Debts recomputation hook.
    Fetches all expenses, splits, and settlements for a group,
    calculates net balances for each group member, runs the debt optimizer,
    and updates the DEBTS table in a single transaction context.
    """
    try:
        # 1. Fetch all members in the group to initialize balance sheet
        members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
        if not members:
            # If no members, clean up and exit
            db.execute(delete(Debt).where(Debt.group_id == group_id))
            return
            
        balances = {m.user_id: 0 for m in members}
        
        # 2. Process all expenses and splits
        expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
        for exp in expenses:
            # The payer gets credited (net balance increases)
            if exp.paid_by in balances:
                balances[exp.paid_by] += exp.amount
            
            # The split participants get debited (net balance decreases)
            for split in exp.splits:
                if split.user_id in balances:
                    balances[split.user_id] -= split.amount
                    
        # 3. Process all settlements
        settlements = db.query(Settlement).filter(Settlement.group_id == group_id).all()
        for setl in settlements:
            # The payer gets credited (they paid off debt, net balance increases)
            if setl.payer_id in balances:
                balances[setl.payer_id] += setl.amount
            # The payee gets debited (they received cash, net balance decreases)
            if setl.payee_id in balances:
                balances[setl.payee_id] -= setl.amount
                
        # 4. Generate optimized debt transactions
        optimized_transactions = optimize_debts(balances)
        
        # 5. Delete old cached debts for this group
        db.execute(delete(Debt).where(Debt.group_id == group_id))
        
        # 6. Insert new optimized debts
        for tx in optimized_transactions:
            debt = Debt(
                group_id=group_id,
                debtor_id=tx["from_user"],
                creditor_id=tx["to_user"],
                amount=tx["amount"]
            )
            db.add(debt)
            
    except Exception as e:
        logger.error(f"Error in recompute_debts for group {group_id}: {e}")
        raise

# --- Expense CRUD ---
def create_expense(
    db: Session,
    group_id: int,
    paid_by: int,
    amount: int,
    description: str | None,
    splits: list[dict]  # List of {"user_id": int, "amount": int}
) -> Expense:
    """
    Creates an expense along with its splits, then runs the debt recomputation hook.
    """
    try:
        # Create core expense
        expense = Expense(
            group_id=group_id,
            paid_by=paid_by,
            amount=amount,
            description=description
        )
        db.add(expense)
        db.flush()  # Generates expense.id
        
        # Create splits
        for split in splits:
            exp_split = ExpenseSplit(
                user_id=split["user_id"],
                amount=split["amount"]
            )
            expense.splits.append(exp_split)
            
        # Recompute derived debts for this group
        recompute_debts(db, group_id)
        
        db.commit()
        db.refresh(expense)
        return expense
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating expense in group {group_id}: {e}")
        raise

def delete_expense(db: Session, expense_id: int) -> bool:
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return False
            
        group_id = expense.group_id
        db.delete(expense)
        
        # Recompute derived debts
        recompute_debts(db, group_id)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting expense {expense_id}: {e}")
        raise

# --- Settlement CRUD ---
def create_settlement(
    db: Session,
    group_id: int,
    payer_id: int,
    payee_id: int,
    amount: int
) -> Settlement:
    """
    Creates a settlement record, then runs the debt recomputation hook.
    """
    try:
        settlement = Settlement(
            group_id=group_id,
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount
        )
        db.add(settlement)
        db.flush()
        
        # Recompute derived debts for this group
        recompute_debts(db, group_id)
        
        db.commit()
        db.refresh(settlement)
        return settlement
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating settlement in group {group_id}: {e}")
        raise

def delete_settlement(db: Session, settlement_id: int) -> bool:
    try:
        settlement = db.query(Settlement).filter(Settlement.id == settlement_id).first()
        if not settlement:
            return False
            
        group_id = settlement.group_id
        db.delete(settlement)
        
        # Recompute derived debts
        recompute_debts(db, group_id)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting settlement {settlement_id}: {e}")
        raise
