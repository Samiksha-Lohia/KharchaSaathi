def optimize_debts(balances: dict[int, int]) -> list[dict]:
    """
    Optimizes group debts using a greedy min-cash-flow algorithm.
    
    Args:
        balances: Dictionary of {user_id: net_balance_in_paise}
        
    Returns:
        List of transactions: [{"from_user": debtor_id, "to_user": creditor_id, "amount": amount_in_paise}]
    """
    # Filter out users with zero balance
    active_balances = {uid: bal for uid, bal in balances.items() if bal != 0}
    
    # Separate into creditors (positive balance) and debtors (negative balance)
    # We store them as lists of [user_id, balance] so we can mutate the balance
    creditors = [[uid, bal] for uid, bal in active_balances.items() if bal > 0]
    debtors = [[uid, bal] for uid, bal in active_balances.items() if bal < 0]
    
    transactions = []
    
    # Run greedy match until all balances are settled
    while creditors and debtors:
        # Sort creditors descending by balance
        creditors.sort(key=lambda x: x[1], reverse=True)
        # Sort debtors ascending by balance (most negative first)
        debtors.sort(key=lambda x: x[1])
        
        creditor = creditors[0]
        debtor = debtors[0]
        
        cred_id, cred_bal = creditor
        debt_id, debt_bal = debtor
        
        # Calculate amount to settle (both values are positive here for comparison)
        debt_abs = abs(debt_bal)
        settle_amount = min(cred_bal, debt_abs)
        
        # Record the transaction
        transactions.append({
            "from_user": debt_id,
            "to_user": cred_id,
            "amount": settle_amount
        })
        
        # Update balances
        creditor[1] -= settle_amount
        debtor[1] += settle_amount
        
        # Remove settled members
        if creditor[1] == 0:
            creditors.pop(0)
        if debtor[1] == 0:
            debtors.pop(0)
            
    return transactions
