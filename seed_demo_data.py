"""
Demo seed script for Money Manager.
Populates the database with realistic but entirely fictional data so you can
run the app immediately after cloning without any personal information.

Run once:
    python seed_demo_data.py
"""

from db import get_db_connection, init_db


def seed_demo():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear any existing data
    for table in ('accounts', 'portfolio', 'goals', 'transactions', 'income_logs', 'expenses', 'transfers'):
        cursor.execute(f"DELETE FROM {table}")

    # Demo account balances
    cursor.execute('''
        INSERT INTO accounts (id, liquid_savings, spending_balance, stock_investment_budget)
        VALUES (1, 2500.00, 320.00, 0.0)
    ''')

    # Demo portfolio -- fictional tickers and costs
    demo_holdings = [
        ('VAS.AX',  20.0,  98.00),   # Vanguard Australian Shares ETF
        ('VGS.AX',  15.0, 112.50),   # Vanguard International Shares ETF
        ('IVV.AX',  10.0,  68.00),   # iShares S&P500 ETF
        ('DHHF.AX', 30.0,  41.00),   # Betashares Diversified All Growth ETF
        ('AAPL',     5.0, 175.00),   # Apple (USD)
        ('MSFT',     3.0, 380.00),   # Microsoft (USD)
    ]

    for ticker, shares, cost in demo_holdings:
        cursor.execute('''
            INSERT INTO portfolio (ticker, shares, avg_cost)
            VALUES (?, ?, ?)
        ''', (ticker, shares, cost))
        cursor.execute('''
            INSERT INTO transactions (type, ticker, shares, price, amount, description)
            VALUES ('BUY', ?, ?, ?, ?, ?)
        ''', (ticker, shares, cost, shares * cost, f'Initial position in {ticker}'))

    # Demo income log entry
    cursor.execute('''
        INSERT INTO transactions (type, amount, description)
        VALUES ('INCOME', 950.00, 'Demo paycheck split: $95 spending / $380 savings / $475 stocks')
    ''')

    # Demo goals
    demo_goals = [
        ('Emergency Fund',       10000.00, 2500.00, 'Savings',   'savings'),
        ('Total Net Worth $50k', 50000.00, 0.0,     'NetWorth',  'net_worth'),
        ('Stock Portfolio $20k', 20000.00, 0.0,     'Portfolio', 'portfolio'),
    ]
    for title, target, current, category, linked in demo_goals:
        cursor.execute('''
            INSERT INTO goals (title, target_amount, current_amount, category, linked_account)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, target, current, category, linked))

    conn.commit()
    conn.close()
    print("Demo data seeded successfully. Visit http://127.0.0.1:5000 to get started.")


if __name__ == '__main__':
    seed_demo()
