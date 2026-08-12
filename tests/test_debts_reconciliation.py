import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db.models import Debt, Expense, Settlement
from app.db.crud import (
    create_user, create_group, add_user_to_group,
    create_expense, create_settlement, delete_expense
)

# Set up in-memory database for testing
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

def test_ledger_debt_reconciliation(db_session):
    # 1. Seed users
    alice = create_user(db_session, "1111111111", "Alice")
    bob = create_user(db_session, "2222222222", "Bob")
    charlie = create_user(db_session, "3333333333", "Charlie")
    
    # 2. Seed group and memberships
    group = create_group(db_session, "Weekend Trip")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    add_user_to_group(db_session, group.id, bob.id, "member")
    add_user_to_group(db_session, group.id, charlie.id, "member")
    
    # 3. Create expense: Alice pays 900 paise. Split equally (300 each)
    splits = [
        {"user_id": alice.id, "amount": 300},
        {"user_id": bob.id, "amount": 300},
        {"user_id": charlie.id, "amount": 300}
    ]
    create_expense(db_session, group.id, alice.id, 900, "Dinner", splits)
    
    # Verify debts: Bob owes Alice 300, Charlie owes Alice 300
    debts = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts) == 2
    
    bob_to_alice = next(d for d in debts if d.debtor_id == bob.id)
    charlie_to_alice = next(d for d in debts if d.debtor_id == charlie.id)
    
    assert bob_to_alice.creditor_id == alice.id
    assert bob_to_alice.amount == 300
    assert charlie_to_alice.creditor_id == alice.id
    assert charlie_to_alice.amount == 300
    
    # 4. Create second expense: Bob pays 600 paise. Split equally (200 each)
    splits2 = [
        {"user_id": alice.id, "amount": 200},
        {"user_id": bob.id, "amount": 200},
        {"user_id": charlie.id, "amount": 200}
    ]
    expense2 = create_expense(db_session, group.id, bob.id, 600, "Taxi", splits2)
    
    # Net balances:
    # Alice: +900 (paid) - 300 (split1) - 200 (split2) = +400
    # Bob: -300 (split1) + 600 (paid) - 200 (split2) = +100
    # Charlie: -300 (split1) - 200 (split2) = -500
    # Expected Debt Output:
    # Charlie owes Alice 400
    # Charlie owes Bob 100
    debts2 = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts2) == 2
    
    charlie_to_alice_2 = next(d for d in debts2 if d.debtor_id == charlie.id and d.creditor_id == alice.id)
    charlie_to_bob_2 = next(d for d in debts2 if d.debtor_id == charlie.id and d.creditor_id == bob.id)
    
    assert charlie_to_alice_2.amount == 400
    assert charlie_to_bob_2.amount == 100
    
    # 5. Record a settlement: Charlie pays Alice 400 paise directly
    create_settlement(db_session, group.id, charlie.id, alice.id, 400)
    
    # Net balances (after settlement of 400 from Charlie to Alice):
    # Alice: +400 - 400 = 0
    # Bob: +100
    # Charlie: -500 + 400 = -100
    # Expected Debt:
    # Charlie owes Bob 100
    debts3 = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts3) == 1
    assert debts3[0].debtor_id == charlie.id
    assert debts3[0].creditor_id == bob.id
    assert debts3[0].amount == 100
    
    # 6. Delete Bob's 600 paise expense to verify rollback recalculation
    delete_expense(db_session, expense2.id)
    
    # State now contains: Dinner expense (Alice paid 900) + Settlement (Charlie paid Alice 400)
    # Net balances:
    # Alice: +900 - 300 (Dinner split) - 400 (received) = +200
    # Bob: -300 (Dinner split)
    # Charlie: -300 (Dinner split) + 400 (paid settlement) = +100
    # Expected Debt:
    # Bob owes Alice 200
    # Bob owes Charlie 100
    debts4 = db_session.query(Debt).filter(Debt.group_id == group.id).all()
    assert len(debts4) == 2
    
    bob_to_alice_4 = next(d for d in debts4 if d.debtor_id == bob.id and d.creditor_id == alice.id)
    bob_to_charlie_4 = next(d for d in debts4 if d.debtor_id == bob.id and d.creditor_id == charlie.id)
    
    assert bob_to_alice_4.amount == 200
    assert bob_to_charlie_4.amount == 100
