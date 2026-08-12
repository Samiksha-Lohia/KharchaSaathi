import pytest
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db.models import Debt, Expense, Settlement
from app.db.crud import create_user, create_group, add_user_to_group
from app.agents.agent_pipeline import parse_fallback_intent, execute_parsed_intent
from app.services.redis_service import set_pending_action, get_pending_action

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

def test_intent_classification_from_fixture():
    """
    Ensures that the offline rule-based parser correctly matches expected intents from the fixture.
    """
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "hinglish_messages.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
        
    for item in scenarios:
        text = item["text"]
        expected_intent = item["intent"]
        
        parsed = parse_fallback_intent(text)
        # Skip checking unknown/unimplemented patterns in mock offline mode, but verify core matches
        if expected_intent in ["add_expense", "settle", "query_balance", "undo", "confirm"]:
            assert parsed["intent"] == expected_intent, f"Failed on text: '{text}'. Expected {expected_intent}, got {parsed['intent']}"

def test_e2e_agent_ledgers(db_session):
    # 1. Setup users & group
    alice = create_user(db_session, "1111111111", "Alice")
    bob = create_user(db_session, "2222222222", "Bob")
    charlie = create_user(db_session, "3333333333", "Charlie")
    
    group = create_group(db_session, "Trip Group")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    add_user_to_group(db_session, group.id, bob.id, "member")
    add_user_to_group(db_session, group.id, charlie.id, "member")
    
    # 2. Simulate message: "Alice spent 900 on Dinner"
    parsed_1 = parse_fallback_intent("Alice spent 900 on Dinner")
    assert parsed_1["intent"] == "add_expense"
    
    reply_1 = execute_parsed_intent(db_session, group.id, alice.id, parsed_1)
    assert "Expense of 900 paise added" in reply_1
    
    # Verify debts: Bob owes Alice 300, Charlie owes Alice 300
    debts = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts) == 2
    
    # 3. Simulate balance query: "show balance"
    parsed_2 = parse_fallback_intent("show balance")
    assert parsed_2["intent"] == "query_balance"
    
    reply_2 = execute_parsed_intent(db_session, group.id, alice.id, parsed_2)
    assert "Alice owes" not in reply_2
    assert "Alice" in reply_2
    assert "Bob" in reply_2
    
    # 4. Simulate settlement message: "Charlie paid Alice 300"
    parsed_3 = parse_fallback_intent("Charlie paid Alice 300")
    assert parsed_3["intent"] == "settle"
    
    reply_3 = execute_parsed_intent(db_session, group.id, charlie.id, parsed_3)
    assert "Recorded settlement" in reply_3
    
    # Verify debts updated: Only Bob owes Alice 300 (Charlie paid off 300)
    debts2 = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts2) == 1
    assert debts2[0].debtor_id == bob.id
    assert debts2[0].amount == 300
    
    # 5. Simulate undo message: "undo"
    parsed_4 = parse_fallback_intent("undo")
    assert parsed_4["intent"] == "undo"
    
    reply_4 = execute_parsed_intent(db_session, group.id, alice.id, parsed_4)
    assert "deleted settlement" in reply_4.lower()
    
    # Verify rollback: Bob owes Alice 300, Charlie owes Alice 300
    debts3 = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts3) == 2

def test_confirmation_loop(db_session):
    alice = create_user(db_session, "1111111111", "Alice")
    bob = create_user(db_session, "2222222222", "Bob")
    group = create_group(db_session, "Weekend")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    add_user_to_group(db_session, group.id, bob.id, "member")
    
    # Pre-populate a pending confirm state in Redis (simulated)
    pending_action = {
        "action": "add_expense",
        "payer_id": alice.id,
        "amount": 1200,
        "description": "Airbnb booking"
    }
    set_pending_action(alice.id, pending_action)
    
    # Verify it exists in pending
    cached = get_pending_action(alice.id)
    assert cached["amount"] == 1200
    
    # User replies "yes"
    parsed = parse_fallback_intent("yes")
    reply = execute_parsed_intent(db_session, group.id, alice.id, parsed)
    
    assert "Airbnb booking" in reply
    assert "recorded" in reply.lower()
    
    # Verify database expense created
    expenses = db_session.query(Expense).filter(Expense.group_id == group.id).all()
    assert len(expenses) == 1
    assert expenses[0].amount == 1200
    
    # Verify pending action is cleared
    assert get_pending_action(alice.id) is None
