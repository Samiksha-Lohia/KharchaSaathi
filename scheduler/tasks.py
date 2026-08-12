from datetime import datetime, timedelta
import logging
from sqlalchemy import func
from app.db.session import get_db
from app.db.models import Debt, Expense, Group, GroupMember, User, Settlement
from app.agents.insight_agent import generate_and_send_nudge
from scheduler.celery_app import app

logger = logging.getLogger(__name__)

# --- Helper Query Logic (Deterministic, No LLM calls) ---

def get_overdue_debts_data(db, days_overdue=7) -> dict[int, list[dict]]:
    """
    Finds debts created more than `days_overdue` ago that remain unpaid.
    Returns: dict of {group_id: [{"debtor_name": str, "creditor_name": str, "amount": int, "days": int}]}
    """
    cutoff = datetime.utcnow() - timedelta(days=days_overdue)
    debts = db.query(Debt).filter(Debt.created_at <= cutoff).all()
    
    group_data = {}
    for d in debts:
        days = (datetime.utcnow() - d.created_at).days
        item = {
            "debtor_id": d.debtor_id,
            "debtor_name": d.debtor.name or f"User {d.debtor_id}",
            "creditor_id": d.creditor_id,
            "creditor_name": d.creditor.name or f"User {d.creditor_id}",
            "amount": d.amount,
            "days_overdue": days
        }
        group_data.setdefault(d.group_id, []).append(item)
    return group_data


def get_weekly_spending_data(db) -> dict[int, dict]:
    """
    Aggregates expenses added in the last 7 days for each group.
    Returns: dict of {group_id: {"total_spending": int, "expenses_count": int}}
    """
    cutoff = datetime.utcnow() - timedelta(days=7)
    results = db.query(
        Expense.group_id,
        func.sum(Expense.amount).label("total"),
        func.count(Expense.id).label("count")
    ).filter(Expense.created_at >= cutoff).group_by(Expense.group_id).all()
    
    return {
        r.group_id: {"total_spending": r.total or 0, "expenses_count": r.count}
        for r in results
    }


def get_inactive_groups_data(db, days_inactive=14) -> list[dict]:
    """
    Identifies groups with no expenses or settlements added in the last `days_inactive` days.
    Returns: list of {"group_id": int, "group_name": str, "days_inactive": int}
    """
    cutoff = datetime.utcnow() - timedelta(days=days_inactive)
    
    # Get all groups
    groups = db.query(Group).all()
    inactive_groups = []
    
    for g in groups:
        # Find latest expense
        latest_exp = db.query(Expense).filter(Expense.group_id == g.id).order_by(Expense.created_at.desc()).first()
        # Find latest settlement
        latest_set = db.query(Settlement).filter(Settlement.group_id == g.id).order_by(Settlement.created_at.desc()).first()
        
        last_activity = g.created_at
        if latest_exp and latest_exp.created_at > last_activity:
            last_activity = latest_exp.created_at
        if latest_set and latest_set.created_at > last_activity:
            last_activity = latest_set.created_at
            
        if last_activity < cutoff:
            days = (datetime.utcnow() - last_activity).days
            inactive_groups.append({
                "group_id": g.id,
                "group_name": g.name,
                "days_inactive": days
            })
            
    return inactive_groups


def get_month_end_data(db) -> dict[int, list[dict]]:
    """
    Aggregates all active debts in groups for month-end settlement suggestion.
    """
    debts = db.query(Debt).all()
    group_data = {}
    for d in debts:
        item = {
            "debtor_name": d.debtor.name or f"User {d.debtor_id}",
            "creditor_name": d.creditor.name or f"User {d.creditor_id}",
            "amount": d.amount
        }
        group_data.setdefault(d.group_id, []).append(item)
    return group_data


# --- Celery Beat Task Wrappers ---

@app.task(name="scheduler.tasks.check_overdue_settlements_task")
def check_overdue_settlements_task():
    logger.info("Executing overdue settlements check task.")
    with get_db() as db:
        overdue_data = get_overdue_debts_data(db, days_overdue=7)
        for group_id, debts_list in overdue_data.items():
            generate_and_send_nudge(db, group_id, "overdue_settlements", {"debts": debts_list})


@app.task(name="scheduler.tasks.weekly_spending_insight_task")
def weekly_spending_insight_task():
    logger.info("Executing weekly spending insights task.")
    with get_db() as db:
        insights_data = get_weekly_spending_data(db)
        for group_id, stats in insights_data.items():
            generate_and_send_nudge(db, group_id, "weekly_spending", stats)


@app.task(name="scheduler.tasks.inactivity_check_task")
def inactivity_check_task():
    logger.info("Executing inactivity check task.")
    with get_db() as db:
        inactive_groups = get_inactive_groups_data(db, days_inactive=14)
        for g in inactive_groups:
            generate_and_send_nudge(db, g["group_id"], "inactivity", g)


@app.task(name="scheduler.tasks.month_end_settle_suggestion_task")
def month_end_settle_suggestion_task():
    logger.info("Executing month-end settlements suggestion task.")
    with get_db() as db:
        month_end_data = get_month_end_data(db)
        for group_id, debts_list in month_end_data.items():
            generate_and_send_nudge(db, group_id, "month_end_settlement", {"debts": debts_list})
