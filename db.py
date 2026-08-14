import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'money_manager.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _safe_alter(cursor, sql):
    """Run an ALTER TABLE statement, silently ignoring if column already exists."""
    try:
        cursor.execute(sql)
    except Exception:
        pass

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

    _safe_alter(cursor, "ALTER TABLE accounts ADD COLUMN dip_fund_budget REAL DEFAULT 0.0")
    
    # Initialize default account record if empty
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO accounts (id, liquid_savings, spending_balance, stock_investment_budget, dip_fund_budget)
            VALUES (1, 0.0, 0.0, 0.0, 0.0)
        ''')

    # Migrate: merge any existing dip_fund_budget into stock_investment_budget
    try:
        cursor.execute("SELECT dip_fund_budget FROM accounts WHERE id = 1")
        row = cursor.fetchone()
        if row and row[0] and row[0] > 0:
            cursor.execute('''
                UPDATE accounts
                SET stock_investment_budget = stock_investment_budget + dip_fund_budget,
                    dip_fund_budget = 0.0
                WHERE id = 1
            ''')
    except Exception:
        pass

    # ===== USER SETTINGS TABLE =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            pay_cycle TEXT DEFAULT 'fortnightly',
            pay_day INTEGER DEFAULT 4,
            last_paycheck_date TEXT DEFAULT '',
            spending_threshold REAL DEFAULT 100.0,
            theme TEXT DEFAULT 'dark',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM user_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO user_settings (id) VALUES (1)")

    # Legacy settings table (kept for backward compat)
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

    # ===== INCOME LOGS =====
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
    _safe_alter(cursor, "ALTER TABLE income_logs ADD COLUMN income_type TEXT DEFAULT 'paycheck'")

    # ===== PORTFOLIO =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            shares REAL NOT NULL,
            avg_cost REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ===== EXPENSES =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_type TEXT NOT NULL,
            expense_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    _safe_alter(cursor, "ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'General'")
    _safe_alter(cursor, "ALTER TABLE expenses ADD COLUMN notes TEXT DEFAULT ''")

    # ===== TRANSFERS =====
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

    # ===== TRANSACTIONS (audit log) =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            ticker TEXT,
            shares REAL,
            price REAL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    _safe_alter(cursor, "ALTER TABLE transactions ADD COLUMN notes TEXT DEFAULT ''")

    # ===== GOALS =====
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
    _safe_alter(cursor, "ALTER TABLE goals ADD COLUMN linked_account TEXT DEFAULT 'none'")
    _safe_alter(cursor, "ALTER TABLE goals ADD COLUMN target_date TEXT")

    # ===== WATCHLIST =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            target_dip_pct REAL DEFAULT 5.0,
            target_price REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ===== NET WORTH SNAPSHOTS (new) =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS net_worth_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            net_worth REAL NOT NULL,
            liquid_savings REAL DEFAULT 0.0,
            spending_balance REAL DEFAULT 0.0,
            stock_budget REAL DEFAULT 0.0,
            portfolio_value REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ===== RECURRING EXPENSES (new) =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'Bills',
            frequency TEXT DEFAULT 'monthly',
            day_of_month INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            last_triggered TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ===== TARGET ALLOCATIONS (new) =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS target_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            target_pct REAL NOT NULL DEFAULT 10.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ===== BROKERAGE FEES (new) =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brokerage_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,
            fee_amount REAL NOT NULL,
            trade_amount REAL DEFAULT 0.0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
