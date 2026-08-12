import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db.models import Debt, Expense, Group, GroupMember, Settlement
from app.db.crud import create_user, create_group, add_user_to_group, create_expense, create_settlement
from scheduler.tasks import (
    get_overdue_debts_data, get_weekly_spending_data,
    get_inactive_groups_data, get_month_end_data
)
from app.agents.insight_agent import (
    check_nudge_rate_limit, is_group_muted, mute_group_nudges,
    generate_insight_text_fallback
)
from app.services.redis_service import redis_client

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_overdue_debts_aggregation(db_session):
    # Seed users and group
    alice = create_user(db_session, "1111111111", "Alice")
    bob = create_user(db_session, "2222222222", "Bob")
    group = create_group(db_session, "Trip")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    add_user_to_group(db_session, group.id, bob.id, "member")
    
    # Create expense and splits
    splits = [
        {"user_id": alice.id, "amount": 100},
        {"user_id": bob.id, "amount": 100}
    ]
    create_expense(db_session, group.id, alice.id, 200, "Dinner", splits)
    
    # Verify we have active debts
    debts = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts) == 1
    
    # Manually backdate the Debt object's created_at to simulate overdue
    debt = debts[0]
    debt.created_at = datetime.utcnow() - timedelta(days=10)
    db_session.commit()
    
    # Execute query
    overdue_data = get_overdue_debts_data(db_session, days_overdue=7)
    assert group.id in overdue_data
    assert len(overdue_data[group.id]) == 1
    assert overdue_data[group.id][0]["debtor_name"] == "Bob"
    assert overdue_data[group.id][0]["amount"] == 100

def test_weekly_spending_aggregation(db_session):
    alice = create_user(db_session, "1111111111", "Alice")
    group = create_group(db_session, "Trip")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    
    splits = [{"user_id": alice.id, "amount": 500}]
    create_expense(db_session, group.id, alice.id, 500, "Hotel", splits)
    
    # Check weekly spending
    spending_data = get_weekly_spending_data(db_session)
    assert group.id in spending_data
    assert spending_data[group.id]["total_spending"] == 500
    assert spending_data[group.id]["expenses_count"] == 1

def test_inactivity_check_aggregation(db_session):
    group = create_group(db_session, "Trip Inactive")
    
    # Make group created_at old
    group.created_at = datetime.utcnow() - timedelta(days=20)
    db_session.commit()
    
    # Run inactivity check (no expenses added, so group should be inactive since creation)
    inactive = get_inactive_groups_data(db_session, days_inactive=14)
    assert len(inactive) == 1
    assert inactive[0]["group_id"] == group.id
    assert inactive[0]["group_name"] == "Trip Inactive"

def test_nudge_rate_limiting_and_muting():
    group_id = 999
    
    # Clear keys in Redis
    redis_client.delete(f"nudge_limit:{group_id}")
    redis_client.delete(f"nudge_mute:{group_id}")
    
    # 1. Check rate limit - first try should succeed
    assert check_nudge_rate_limit(group_id) is True
    # Second try should fail due to rate-limit
    assert check_nudge_rate_limit(group_id) is False
    
    # 2. Check mute state - should not be muted
    assert is_group_muted(group_id) is False
    # Mute group
    mute_group_nudges(group_id, duration_seconds=10)
    assert is_group_muted(group_id) is True

def test_insight_text_fallback_phrasing():
    data = {
        "debts": [
            {"debtor_name": "Bob", "creditor_name": "Alice", "amount": 300, "days_overdue": 8}
        ]
    }
    phrased = generate_insight_text_fallback("overdue_settlements", data)
    assert "Bob owes Alice 300" in phrased
    assert "overdue" in phrased.lower()
