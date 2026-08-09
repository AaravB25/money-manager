import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'money_manager.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Accounts summary table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY DEFAULT 1,
            liquid_savings REAL DEFAULT 0.0,
            spending_balance REAL DEFAULT 0.0,
            stock_investment_budget REAL DEFAULT 0.0,
            dip_fund_budget REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        cursor.execute("ALTER TABLE accounts ADD COLUMN dip_fund_budget REAL DEFAULT 0.0")
    except Exception:
        pass
    
    # Initialize default account record if empty
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO accounts (id, liquid_savings, spending_balance, stock_investment_budget, dip_fund_budget)
            VALUES (1, 0.0, 0.0, 0.0, 0.0)
        ''')

    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            spending_pct REAL DEFAULT 10.0,
            savings_pct REAL DEFAULT 90.0,
            stock_target_per_pay REAL DEFAULT 500.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO settings (id, spending_pct, savings_pct, stock_target_per_pay)
            VALUES (1, 10.0, 90.0, 500.0)
        ''')

    # Income logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            spending_amount REAL NOT NULL,
            savings_amount REAL NOT NULL,
            stock_allocation REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Stock portfolio holdings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            shares REAL NOT NULL,
            avg_cost REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Expenses & Balance sync table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_type TEXT NOT NULL, -- 'spending' or 'savings'
            expense_type TEXT NOT NULL, -- 'preset', 'sync', 'savings_withdrawal', 'direct'
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Inter-account transfers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_account TEXT NOT NULL,
            to_account TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Complete audit transaction log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, -- 'INCOME', 'EXPENSE', 'TRANSFER', 'BUY', 'SELL'
            ticker TEXT,
            shares REAL,
            price REAL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Financial goals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            category TEXT NOT NULL,
            linked_account TEXT DEFAULT 'none',
            target_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add linked_account column if upgrading from older schema
    try:
        cursor.execute("ALTER TABLE goals ADD COLUMN linked_account TEXT DEFAULT 'none'")
    except Exception:
        pass

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
