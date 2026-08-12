import pytest
from app.algorithms.debt_optimizer import optimize_debts

def test_two_person_simple_split():
    """
    Case 1: Simple 2-person split.
    User 1 paid and User 2 owes.
    Balances: User 1: +500 paise, User 2: -500 paise.
    """
    balances = {
        1: 500,
        2: -500
    }
    transactions = optimize_debts(balances)
    assert len(transactions) == 1
    assert transactions[0] == {"from_user": 2, "to_user": 1, "amount": 500}

def test_four_person_split():
    """
    Case 2: 4-person split.
    Balances:
    User 1: +1000 paise (Creditor)
    User 2: +400 paise (Creditor)
    User 3: -900 paise (Debtor)
    User 4: -500 paise (Debtor)
    Total net balance must sum to 0.
    """
    balances = {
        1: 1000,
        2: 400,
        3: -900,
        4: -500
    }
    transactions = optimize_debts(balances)
    # The greedy min-cash-flow algorithm should match:
    # 1. Largest debtor (User 3: -900) with largest creditor (User 1: +1000)
    #    User 3 pays User 1: 900 paise.
    #    Balances after transaction 1: User 1: +100, User 2: +400, User 3: 0, User 4: -500.
    # 2. Next largest debtor (User 4: -500) with largest creditor (User 2: +400)
    #    User 4 pays User 2: 400 paise.
    #    Balances after transaction 2: User 1: +100, User 2: 0, User 3: 0, User 4: -100.
    # 3. User 4 pays User 1: 100 paise.
    #    Balances after transaction 3: all zero.
    assert len(transactions) == 3
    # Check that the transactions correctly settle the balances
    net_effects = {uid: 0 for uid in balances}
    for t in transactions:
        net_effects[t["from_user"]] -= t["amount"]
        net_effects[t["to_user"]] += t["amount"]
    
    for uid in balances:
        assert net_effects[uid] == balances[uid]

def test_circular_debt_loop():
    """
    Case 3: Fully circular debt: A -> B -> C -> A
    Under normal splits, circular debt naturally cancels out to net 0 balances.
    If net balances are 0, no transactions should be generated.
    """
    # Net balances for A, B, C after the circle cancels out are all 0
    balances = {
        1: 0,
        2: 0,
        3: 0
    }
    transactions = optimize_debts(balances)
    assert len(transactions) == 0

def test_partial_settlement():
    """
    Case 4: A partial settlement mid-cycle.
    Say User 1 owes User 2 1000 paise, but User 1 has paid 400 paise to User 2 directly.
    Net balance would be: User 1: -600, User 2: +600.
    """
    balances = {
        1: -600,
        2: 600
    }
    transactions = optimize_debts(balances)
    assert len(transactions) == 1
    assert transactions[0] == {"from_user": 1, "to_user": 2, "amount": 600}

def test_rounding_edge_case():
    """
    Case 5: A rounding edge case with odd paise split.
    Say 100 paise is split across 3 people.
    Person 1 paid 100.
    Person 2 and 3 owe 33 paise, and Person 1 owes 34 paise (to sum to 100).
    Wait, the net balances:
    Person 1: 100 - 34 = +66 paise
    Person 2: 0 - 33 = -33 paise
    Person 3: 0 - 33 = -33 paise
    Sum of balances: +66 - 33 - 33 = 0.
    """
    balances = {
        1: 66,
        2: -33,
        3: -33
    }
    transactions = optimize_debts(balances)
    assert len(transactions) == 2
    # Ensure they settle exactly
    net_effects = {uid: 0 for uid in balances}
    for t in transactions:
        net_effects[t["from_user"]] -= t["amount"]
        net_effects[t["to_user"]] += t["amount"]
    
    for uid in balances:
        assert net_effects[uid] == balances[uid]
