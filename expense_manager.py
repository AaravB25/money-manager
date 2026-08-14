from db import get_db_connection

def sync_spending_balance(new_balance, description="Spending Balance Sync", category="General", notes=""):
    """
    Directly sets the spending balance to `new_balance`.
    If new_balance < current_balance, records difference as spending expense.
    If new_balance > current_balance, adjusts spending balance upward.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT spending_balance FROM accounts WHERE id = 1")
    row = cursor.fetchone()
    current_balance = row['spending_balance'] if row else 0.0
    
    diff = round(current_balance - new_balance, 2)
    
    if diff > 0:
        # User spent diff amount
        expense_desc = description if description else "Spending Balance Adjustment"
        cursor.execute('''
            INSERT INTO expenses (account_type, expense_type, amount, description, category, notes)
            VALUES ('spending', 'sync', ?, ?, ?, ?)
        ''', (diff, expense_desc, category, notes))
        
        cursor.execute('''
            INSERT INTO transactions (type, amount, description)
            VALUES ('EXPENSE', ?, ?)
        ''', (diff, f"[SPENDING SYNC] {expense_desc}"))
        
    elif diff < 0:
        # Spending balance added/adjusted upward
        cursor.execute('''
            INSERT INTO transactions (type, amount, description)
            VALUES ('INCOME', ?, ?)
        ''', (abs(diff), f"[SPENDING ADJUSTMENT] {description}"))
        
    cursor.execute("UPDATE accounts SET spending_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_balance,))
    conn.commit()
    conn.close()
    
    return {
        'previous_balance': current_balance,
        'new_balance': new_balance,
        'difference': diff
    }

def quick_deduct_spending(amount, description="Quick Spending Expense", category="General", notes=""):
    """
    Quickly deducts `amount` from spending account.
    """
    amount = float(amount)
    if amount <= 0:
        return {'success': False, 'error': 'Amount must be positive'}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT spending_balance FROM accounts WHERE id = 1")
    current_balance = cursor.fetchone()['spending_balance']
    new_balance = round(current_balance - amount, 2)
    
    cursor.execute("UPDATE accounts SET spending_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_balance,))
    
    cursor.execute('''
        INSERT INTO expenses (account_type, expense_type, amount, description, category, notes)
        VALUES ('spending', 'preset', ?, ?, ?, ?)
    ''', (amount, description, category, notes))
    
    cursor.execute('''
        INSERT INTO transactions (type, amount, description)
        VALUES ('EXPENSE', ?, ?)
    ''', (amount, f"[SPENDING DEDUCT] {description}"))
    
    conn.commit()
    conn.close()
    
    return {'success': True, 'new_balance': new_balance, 'deducted': amount}

def withdraw_from_savings(amount, description="Savings Withdrawal", category="Savings", notes=""):
    """
    Deducts `amount` directly from Liquid Savings for emergency/major expenses.
    """
    amount = float(amount)
    if amount <= 0:
        return {'success': False, 'error': 'Amount must be positive'}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT liquid_savings FROM accounts WHERE id = 1")
    current_savings = cursor.fetchone()['liquid_savings']
    
    if amount > current_savings:
        conn.close()
        return {'success': False, 'error': f'Insufficient liquid savings balance (${current_savings:.2f})'}
        
    new_savings = round(current_savings - amount, 2)
    
    cursor.execute("UPDATE accounts SET liquid_savings = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_savings,))
    
    cursor.execute('''
        INSERT INTO expenses (account_type, expense_type, amount, description, category, notes)
        VALUES ('savings', 'savings_withdrawal', ?, ?, ?, ?)
    ''', (amount, description, category, notes))
    
    cursor.execute('''
        INSERT INTO transactions (type, amount, description)
        VALUES ('EXPENSE', ?, ?)
    ''', (amount, f"[SAVINGS WITHDRAWAL] {description}"))
    
    conn.commit()
    conn.close()
    
    return {'success': True, 'new_savings_balance': new_savings, 'withdrawn': amount}

def transfer_funds(from_account, to_account, amount, description="Account Transfer"):
    """
    Transfers funds between accounts: 'savings', 'spending', 'stock_budget'.
    """
    amount = float(amount)
    if amount <= 0:
        return {'success': False, 'error': 'Transfer amount must be positive'}
        
    valid_accounts = ['savings', 'spending', 'stock_budget', 'dip_fund']
    if from_account not in valid_accounts or to_account not in valid_accounts:
        return {'success': False, 'error': 'Invalid account selection'}
        
    if from_account == to_account:
        return {'success': False, 'error': 'Source and destination accounts must be different'}
        
    account_column_map = {
        'savings': 'liquid_savings',
        'spending': 'spending_balance',
        'stock_budget': 'stock_investment_budget',
        'dip_fund': 'dip_fund_budget'
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    from_col = account_column_map[from_account]
    to_col = account_column_map[to_account]
    
    cursor.execute(f"SELECT {from_col}, {to_col} FROM accounts WHERE id = 1")
    row = cursor.fetchone()
    
    from_bal = row[from_col]
    to_bal = row[to_col]
    
    if amount > from_bal:
        conn.close()
        return {'success': False, 'error': f'Insufficient balance in {from_account} (${from_bal:.2f})'}
        
    new_from_bal = round(from_bal - amount, 2)
    new_to_bal = round(to_bal + amount, 2)
    
    cursor.execute(f"UPDATE accounts SET {from_col} = ?, {to_col} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_from_bal, new_to_bal))
    
    cursor.execute('''
        INSERT INTO transfers (from_account, to_account, amount, description)
        VALUES (?, ?, ?, ?)
    ''', (from_account, to_account, amount, description))
    
    cursor.execute('''
        INSERT INTO transactions (type, amount, description)
        VALUES ('TRANSFER', ?, ?)
    ''', (amount, f"[TRANSFER] {amount:.2f} from {from_account} to {to_account} ({description})"))
    
    conn.commit()
    conn.close()
    
    return {'success': True, 'from_account': from_account, 'to_account': to_account, 'amount': amount}
