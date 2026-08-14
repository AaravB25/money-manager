from flask import Flask, render_template, request, jsonify, Response
import csv
import io
import os
import time
from db import init_db, get_db_connection
from calculator import calculate_pay_split
from stock_tracker import fetch_stock_quote, fetch_multiple_quotes, fetch_aud_usd_rate, fetch_multiple_dividend_yields
from simulations import calculate_compound_interest, calculate_personalized_net_worth_projection, calculate_wealth_plan
from expense_manager import (
    sync_spending_balance,
    quick_deduct_spending,
    withdraw_from_savings,
    transfer_funds
)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

STOCK_NAMES = {
    'CBA.AX': 'Commonwealth Bank of Australia',
    'DHHF.AX': 'BetaShares Diversified All Growth ETF',
    'IVV.AX': 'iShares S&P 500 AUD ETF',
    'NDQ.AX': 'Betashares Nasdaq 100 ETF',
    'VAE.AX': 'Vanguard FTSE Asia ex Japan Shares Index ETF',
    'VAS.AX': 'Vanguard Australian Shares Index ETF',
    'VHY.AX': 'Vanguard Australian Shares High Yield ETF',
    'XMET.AX': 'Betashares Energy Transition Metals ETF',
    'GPRO': 'GoPro, Inc.',
    'TSLA': 'Tesla, Inc.'
}

STOCK_CACHE = {}

@app.before_request
def setup_database():
    init_db()

@app.route('/')
def index():
    build_ts = int(time.time())
    return render_template('index.html', build_ts=build_ts)

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT liquid_savings, spending_balance, stock_investment_budget FROM accounts WHERE id = 1")
    acc = cursor.fetchone()
    liquid_savings = acc['liquid_savings'] if acc else 0.0
    spending_balance = acc['spending_balance'] if acc else 0.0
    stock_budget = acc['stock_investment_budget'] if acc else 0.0
    
    cursor.execute("SELECT ticker, shares, avg_cost FROM portfolio")
    holdings = [dict(row) for row in cursor.fetchall()]
    
    symbols = [h['ticker'] for h in holdings]
    if symbols:
        quotes = fetch_multiple_quotes(symbols)
        STOCK_CACHE.update(quotes)
            
    aud_usd_rate = fetch_aud_usd_rate()
    
    portfolio_value_aud = 0.0
    total_cost_aud = 0.0
    
    for h in holdings:
        sym = h['ticker']
        quote = STOCK_CACHE.get(sym, {})
        current_price = quote.get('current_price', h['avg_cost'])
        is_asx = sym.endswith('.AX')
        multiplier = 1.0 if is_asx else aud_usd_rate
        
        mkt_val = h['shares'] * current_price * multiplier
        cost_val = h['shares'] * h['avg_cost'] * multiplier
        
        portfolio_value_aud += mkt_val
        total_cost_aud += cost_val
        
    total_gain_loss_aud = portfolio_value_aud - total_cost_aud
    gain_loss_pct = (total_gain_loss_aud / total_cost_aud * 100) if total_cost_aud > 0 else 0.0
    net_worth_aud = round(liquid_savings + spending_balance + stock_budget + portfolio_value_aud, 2)
    
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 5")
    recent_transactions = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM goals ORDER BY created_at DESC")
    goals = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'net_worth': net_worth_aud,
        'liquid_savings': round(liquid_savings, 2),
        'spending_balance': round(spending_balance, 2),
        'stock_investment_budget': round(stock_budget, 2),
        'portfolio_value': round(portfolio_value_aud, 2),
        'total_cost': round(total_cost_aud, 2),
        'total_gain_loss': round(total_gain_loss_aud, 2),
        'gain_loss_pct': round(gain_loss_pct, 2),
        'holdings_count': len(holdings),
        'aud_usd_rate': aud_usd_rate,
        'recent_transactions': recent_transactions,
        'goals': goals
    })

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT ticker, shares, avg_cost FROM portfolio ORDER BY ticker ASC")
    holdings = [dict(row) for row in cursor.fetchall()]
    
    symbols = [h['ticker'] for h in holdings]
    if symbols:
        quotes = fetch_multiple_quotes(symbols)
        STOCK_CACHE.update(quotes)
        
    aud_usd_rate = fetch_aud_usd_rate()
    
    enriched = []
    total_val_aud = 0.0
    total_cost_aud = 0.0
    
    for h in holdings:
        sym = h['ticker']
        quote = STOCK_CACHE.get(sym, {})
        current_price = quote.get('current_price', h['avg_cost'])
        change = quote.get('change', 0.0)
        change_pct = quote.get('change_percent', 0.0)
        
        is_asx = sym.endswith('.AX')
        currency = 'AUD' if is_asx else 'USD'
        multiplier = 1.0 if is_asx else aud_usd_rate
        
        native_mkt_val = round(h['shares'] * current_price, 2)
        native_cost_basis = round(h['shares'] * h['avg_cost'], 2)
        native_gain_loss = round(native_mkt_val - native_cost_basis, 2)
        gain_loss_pct = round((native_gain_loss / native_cost_basis * 100), 2) if native_cost_basis > 0 else 0.0
        
        aud_mkt_val = round(native_mkt_val * multiplier, 2)
        aud_cost_basis = round(native_cost_basis * multiplier, 2)
        aud_gain_loss = round(aud_mkt_val - aud_cost_basis, 2)
        
        total_val_aud += aud_mkt_val
        total_cost_aud += aud_cost_basis
        
        clean_code = sym.replace('.AX', '') if is_asx else sym
        name = STOCK_NAMES.get(sym, quote.get('name', clean_code))
        
        enriched.append({
            'ticker': sym,
            'code': clean_code,
            'name': name,
            'exchange': 'ASX' if is_asx else 'US',
            'shares': h['shares'],
            'avg_cost': h['avg_cost'],
            'current_price': current_price,
            'market_value_native': native_mkt_val,
            'cost_basis_native': native_cost_basis,
            'gain_loss_native': native_gain_loss,
            'market_value_aud': aud_mkt_val,
            'cost_basis_aud': aud_cost_basis,
            'gain_loss_aud': aud_gain_loss,
            'gain_loss_pct': gain_loss_pct,
            'daily_change': change,
            'daily_change_pct': change_pct,
            'currency': currency
        })
        
    conn.close()
    
    total_gain_loss_aud = round(total_val_aud - total_cost_aud, 2)
    total_gain_loss_pct = round((total_gain_loss_aud / total_cost_aud * 100), 2) if total_cost_aud > 0 else 0.0
    
    return jsonify({
        'holdings': enriched,
        'total_value_aud': round(total_val_aud, 2),
        'total_cost_aud': round(total_cost_aud, 2),
        'total_gain_loss_aud': total_gain_loss_aud,
        'total_gain_loss_pct': total_gain_loss_pct,
        'aud_usd_rate': aud_usd_rate
    })

@app.route('/api/portfolio/refresh', methods=['POST'])
def refresh_portfolio_prices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM portfolio")
    symbols = [row['ticker'] for row in cursor.fetchall()]
    conn.close()
    
    if symbols:
        STOCK_CACHE.clear()
        quotes = fetch_multiple_quotes(symbols)
        STOCK_CACHE.update(quotes)
        return jsonify({'success': True, 'refreshed_count': len(symbols)})
    return jsonify({'success': True, 'refreshed_count': 0})

@app.route('/api/portfolio/add', methods=['POST'])
def add_holding():
    data = request.json or {}
    ticker = data.get('ticker', '').strip().upper()
    try:
        shares = float(data.get('shares', 0.0))
        avg_cost = float(data.get('avg_cost', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid shares or cost basis'}), 400
        
    if not ticker or shares <= 0 or avg_cost < 0:
        return jsonify({'error': 'Ticker and valid positive shares/cost are required'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT shares, avg_cost FROM portfolio WHERE ticker = ?", (ticker,))
    existing = cursor.fetchone()
    
    if existing:
        old_shares = existing['shares']
        old_cost = existing['avg_cost']
        new_shares = old_shares + shares
        new_avg_cost = ((old_shares * old_cost) + (shares * avg_cost)) / new_shares
        cursor.execute("UPDATE portfolio SET shares = ?, avg_cost = ?, updated_at = CURRENT_TIMESTAMP WHERE ticker = ?", (new_shares, new_avg_cost, ticker))
    else:
        cursor.execute("INSERT INTO portfolio (ticker, shares, avg_cost) VALUES (?, ?, ?)", (ticker, shares, avg_cost))
        
    cursor.execute('''
        INSERT INTO transactions (type, ticker, shares, price, amount, description)
        VALUES ('BUY', ?, ?, ?, ?, ?)
    ''', (ticker, shares, avg_cost, shares * avg_cost, f"[MANUAL HOLDING ADD] Added {shares} shares of {ticker} @ ${avg_cost:.2f}"))
    
    conn.commit()
    conn.close()
    
    STOCK_CACHE[ticker] = fetch_stock_quote(ticker)
    return jsonify({'success': True, 'ticker': ticker, 'shares': shares})

@app.route('/api/trade', methods=['POST'])
def execute_trade():
    data = request.json or {}
    action = data.get('action', '').upper()
    ticker = data.get('ticker', '').strip().upper()
    try:
        shares = float(data.get('shares', 0.0))
        price = float(data.get('price', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid trade inputs'}), 400
        
    if action not in ['BUY', 'SELL'] or not ticker or shares <= 0 or price <= 0:
        return jsonify({'error': 'Valid action, ticker, shares, and price required'}), 400
        
    total_amount = round(shares * price, 2)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT liquid_savings, stock_investment_budget FROM accounts WHERE id = 1")
    acc = cursor.fetchone()
    stock_budget = acc['stock_investment_budget']
    savings = acc['liquid_savings']
    
    if action == 'BUY':
        if stock_budget >= total_amount:
            new_budget = round(stock_budget - total_amount, 2)
            cursor.execute("UPDATE accounts SET stock_investment_budget = ? WHERE id = 1", (new_budget,))
        elif (stock_budget + savings) >= total_amount:
            remainder = total_amount - stock_budget
            new_savings = round(savings - remainder, 2)
            cursor.execute("UPDATE accounts SET stock_investment_budget = 0.0, liquid_savings = ? WHERE id = 1", (new_savings,))
        else:
            conn.close()
            return jsonify({'error': f'Insufficient funds (${stock_budget + savings:.2f} available) for purchase'}), 400
            
        cursor.execute("SELECT shares, avg_cost FROM portfolio WHERE ticker = ?", (ticker,))
        existing = cursor.fetchone()
        if existing:
            old_s = existing['shares']
            old_c = existing['avg_cost']
            n_s = old_s + shares
            n_c = ((old_s * old_c) + total_amount) / n_s
            cursor.execute("UPDATE portfolio SET shares = ?, avg_cost = ?, updated_at = CURRENT_TIMESTAMP WHERE ticker = ?", (n_s, n_c, ticker))
        else:
            cursor.execute("INSERT INTO portfolio (ticker, shares, avg_cost) VALUES (?, ?, ?)", (ticker, shares, price))
            
        desc = f"[TRADE BUY] Bought {shares} shares of {ticker} @ ${price:.2f}"
        
    elif action == 'SELL':
        cursor.execute("SELECT shares, avg_cost FROM portfolio WHERE ticker = ?", (ticker,))
        existing = cursor.fetchone()
        if not existing or existing['shares'] < shares:
            conn.close()
            return jsonify({'error': 'Insufficient shares available'}), 400
            
        remaining = existing['shares'] - shares
        if remaining <= 0:
            cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
        else:
            cursor.execute("UPDATE portfolio SET shares = ?, updated_at = CURRENT_TIMESTAMP WHERE ticker = ?", (remaining, ticker))
            
        new_savings = round(savings + total_amount, 2)
        cursor.execute("UPDATE accounts SET liquid_savings = ? WHERE id = 1", (new_savings,))
        desc = f"[TRADE SELL] Sold {shares} shares of {ticker} @ ${price:.2f}"
        
    cursor.execute('''
        INSERT INTO transactions (type, ticker, shares, price, amount, description)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (action, ticker, shares, price, total_amount, desc))
    
    conn.commit()
    conn.close()
    
    STOCK_CACHE[ticker] = fetch_stock_quote(ticker)
    return jsonify({'success': True, 'action': action, 'ticker': ticker, 'shares': shares})

@app.route('/api/income', methods=['POST'])
def add_income():
    data = request.json or {}
    description = data.get('description', 'Paycheck').strip()
    try:
        amount = float(data.get('amount', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid income amount'}), 400
        
    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than zero'}), 400
        
    spending_pct = float(data.get('spending_pct', 10.0))
    savings_pct = float(data.get('savings_pct', 40.0))
    stock_pct = float(data.get('stock_pct', 50.0))
    
    split = calculate_pay_split(amount, spending_pct, savings_pct, stock_pct)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO income_logs (description, amount, spending_amount, savings_amount, stock_allocation)
        VALUES (?, ?, ?, ?, ?)
    ''', (description, split['pay_amount'], split['spending_amount'], split['savings_amount'], split['stock_allocation']))
    
    cursor.execute('''
        UPDATE accounts
        SET liquid_savings = liquid_savings + ?,
            spending_balance = spending_balance + ?,
            stock_investment_budget = stock_investment_budget + ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (split['savings_amount'], split['spending_amount'], split['active_stock_allocation']))
    
    audit_desc = f"[INCOME] {description}: ${amount:.2f} | Spending: +${split['spending_amount']:.2f} | Savings: +${split['savings_amount']:.2f} | Stock Budget: +${split['active_stock_allocation']:.2f}"
    # Store split details in description for undo capability
    cursor.execute('''
        INSERT INTO transactions (type, amount, description)
        VALUES ('INCOME', ?, ?)
    ''', (amount, audit_desc))
    income_tx_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Income of ${amount:.2f} recorded.', 'split': split, 'transaction_id': income_tx_id})

@app.route('/api/expenses/sync', methods=['POST'])
def handle_spending_sync():
    data = request.json or {}
    try:
        new_balance = float(data.get('new_balance', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid balance amount'}), 400
    description = data.get('description', 'Spending Balance Sync')
    result = sync_spending_balance(new_balance, description)
    return jsonify({'success': True, 'data': result})

@app.route('/api/expenses/quick', methods=['POST'])
def handle_quick_expense():
    data = request.json or {}
    try:
        amount = float(data.get('amount', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid expense amount'}), 400
    description = data.get('description', 'Quick Spending Expense')
    result = quick_deduct_spending(amount, description)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/expenses/savings', methods=['POST'])
def handle_savings_withdrawal():
    data = request.json or {}
    try:
        amount = float(data.get('amount', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid withdrawal amount'}), 400
    description = data.get('description', 'Savings Withdrawal')
    result = withdraw_from_savings(amount, description)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/transfer', methods=['POST'])
def handle_transfer():
    data = request.json or {}
    from_acc = data.get('from_account')
    to_acc = data.get('to_account')
    try:
        amount = float(data.get('amount', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid transfer amount'}), 400
    description = data.get('description', 'Account Transfer')
    result = transfer_funds(from_acc, to_acc, amount, description)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

# --- UNDO TRANSACTION ---
@app.route('/api/transactions/undo/<int:tx_id>', methods=['POST'])
def undo_transaction(tx_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,))
    tx = cursor.fetchone()
    if not tx:
        conn.close()
        return jsonify({'error': 'Transaction not found'}), 404

    tx = dict(tx)
    tx_type = tx['type']

    if tx_type == 'INCOME':
        # Parse amounts back from description using stored split amounts
        import re
        desc = tx['description']
        spending = savings = stock = 0.0
        m = re.search(r'Spending: \+\$([\d.]+)', desc)
        if m: spending = float(m.group(1))
        m = re.search(r'Savings: \+\$([\d.]+)', desc)
        if m: savings = float(m.group(1))
        m = re.search(r'Stock Budget: \+\$([\d.]+)', desc)
        if m: stock = float(m.group(1))

        cursor.execute('''
            UPDATE accounts
            SET liquid_savings = MAX(0, liquid_savings - ?),
                spending_balance = MAX(0, spending_balance - ?),
                stock_investment_budget = MAX(0, stock_investment_budget - ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (savings, spending, stock))

    elif tx_type == 'EXPENSE':
        # Restore spending balance
        cursor.execute('''
            UPDATE accounts SET spending_balance = spending_balance + ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1
        ''', (abs(tx['amount']),))

    else:
        conn.close()
        return jsonify({'error': f'Cannot undo transaction type "{tx_type}" automatically. Please adjust balances manually via the transfer tool.'}), 400

    undo_desc = f"[UNDO] Reversed transaction #{tx_id}: {tx['description'][:80]}"
    cursor.execute("INSERT INTO transactions (type, amount, description) VALUES ('UNDO', ?, ?)",
                   (-abs(tx['amount']), undo_desc))
    cursor.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'Transaction #{tx_id} reversed successfully.'})

# --- LIST ALL TRANSACTIONS ---
@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    limit = request.args.get('limit', 20, type=int)
    cursor.execute('SELECT * FROM transactions ORDER BY date DESC LIMIT ?', (limit,))
    txs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'transactions': txs})

@app.route('/api/goals', methods=['GET', 'POST', 'DELETE'])
def handle_goals():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'DELETE':
        goal_id = request.args.get('id')
        if not goal_id:
            conn.close()
            return jsonify({'error': 'Goal ID required'}), 400
        cursor.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'POST':
        data = request.json or {}
        title = data.get('title', '').strip()
        category = data.get('category', 'Savings')
        linked_account = data.get('linked_account', 'none')
        try:
            target = float(data.get('target_amount', 0.0))
            current = float(data.get('current_amount', 0.0))
        except ValueError:
            conn.close()
            return jsonify({'error': 'Invalid goal amounts'}), 400
            
        if not title or target <= 0:
            conn.close()
            return jsonify({'error': 'Goal title and valid positive target amount are required'}), 400
            
        cursor.execute('''
            INSERT INTO goals (title, target_amount, current_amount, category, linked_account)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, target, current, category, linked_account))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Goal "{title}" created successfully.'})
        
    # GET: resolve live balances for linked goals
    cursor.execute('SELECT liquid_savings, spending_balance, stock_investment_budget FROM accounts WHERE id = 1')
    acc = cursor.fetchone()
    liquid_savings = acc['liquid_savings'] if acc else 0.0
    spending_balance = acc['spending_balance'] if acc else 0.0
    stock_budget = acc['stock_investment_budget'] if acc else 0.0

    # Live portfolio value
    cursor.execute('SELECT ticker, shares, avg_cost FROM portfolio')
    holdings = [dict(row) for row in cursor.fetchall()]
    aud_usd_rate = fetch_aud_usd_rate()
    portfolio_value = sum(
        h['shares'] * STOCK_CACHE.get(h['ticker'], {}).get('current_price', h['avg_cost']) *
        (1.0 if h['ticker'].endswith('.AX') else aud_usd_rate)
        for h in holdings
    )
    net_worth = liquid_savings + spending_balance + stock_budget + portfolio_value

    ACCOUNT_VALUES = {
        'savings': liquid_savings,
        'spending': spending_balance,
        'stock_budget': stock_budget,
        'portfolio': portfolio_value,
        'net_worth': net_worth,
        'none': None
    }

    cursor.execute('SELECT * FROM goals ORDER BY created_at DESC')
    raw_goals = [dict(row) for row in cursor.fetchall()]
    conn.close()

    goals = []
    for g in raw_goals:
        linked = g.get('linked_account', 'none') or 'none'
        if linked != 'none' and linked in ACCOUNT_VALUES:
            g['current_amount'] = round(ACCOUNT_VALUES[linked], 2)
            g['live_linked'] = True
        else:
            g['live_linked'] = False
        goals.append(g)

    return jsonify({'goals': goals})

@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.json or {}
    sim_type = data.get('type', 'projection')
    
    if sim_type == 'compound':
        initial = data.get('initial_amount', 1000.0)
        monthly = data.get('monthly_contribution', 500.0)
        rate = data.get('annual_interest_rate', 8.0)
        years = data.get('years', 10)
        res = calculate_compound_interest(initial, monthly, rate, years)
        return jsonify({'success': True, 'simulation': res})
        
    elif sim_type == 'projection':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT liquid_savings, spending_balance FROM accounts WHERE id = 1")
        acc = cursor.fetchone()
        savings = acc['liquid_savings'] if acc else 0.0
        spending = acc['spending_balance'] if acc else 0.0
        
        cursor.execute("SELECT ticker, shares, avg_cost FROM portfolio")
        holdings = [dict(row) for row in cursor.fetchall()]
        
        aud_usd_rate = fetch_aud_usd_rate()
        port_val_aud = sum(h['shares'] * STOCK_CACHE.get(h['ticker'], {}).get('current_price', h['avg_cost']) * (1.0 if h['ticker'].endswith('.AX') else aud_usd_rate) for h in holdings)
        conn.close()
        
        pay = data.get('pay_amount', 950.0)
        pay_freq = data.get('pay_frequency', 'fortnightly')
        stock_return = data.get('stock_annual_return', 8.0)
        savings_return = data.get('savings_annual_return', 4.0)
        years = data.get('years', 30)
        
        res = calculate_personalized_net_worth_projection(
            savings, port_val_aud, spending, pay, pay_freq,
            spending_pct=10.0, savings_pct=40.0, stock_pct=50.0,
            stock_annual_return=stock_return, savings_annual_return=savings_return,
            years=years
        )
        return jsonify({'success': True, 'simulation': res})
        
    return jsonify({'error': 'Invalid simulation type'}), 400

@app.route('/api/wealth-plan', methods=['POST'])
def run_wealth_plan():
    data = request.json or {}
    events = data.get('events', [])
    config = data.get('config', {})

    # Auto-fill starting state from current DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT liquid_savings, spending_balance, stock_investment_budget FROM accounts WHERE id = 1')
    acc = cursor.fetchone()
    cursor.execute('SELECT ticker, shares, avg_cost FROM portfolio')
    holdings = [dict(row) for row in cursor.fetchall()]
    conn.close()

    aud_usd_rate = fetch_aud_usd_rate()
    portfolio_value = sum(
        h['shares'] * STOCK_CACHE.get(h['ticker'], {}).get('current_price', h['avg_cost']) *
        (1.0 if h['ticker'].endswith('.AX') else aud_usd_rate)
        for h in holdings
    )

    starting_state = {
        'savings': acc['liquid_savings'] if acc else 0.0,
        'portfolio': portfolio_value,
        'spending': acc['spending_balance'] if acc else 0.0,
        'stock_budget': acc['stock_investment_budget'] if acc else 0.0
    }

    result = calculate_wealth_plan(starting_state, events, config)
    return jsonify({'success': True, 'plan': result})

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 100")
    txs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'transactions': txs})

@app.route('/api/export', methods=['GET'])
def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, ticker, shares, price, amount, description, date FROM transactions ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Type', 'Ticker', 'Shares', 'Price', 'Amount', 'Description', 'Date'])
    for r in rows:
        writer.writerow([r['id'], r['type'], r['ticker'] or '', r['shares'] or '', r['price'] or '', r['amount'], r['description'], r['date']])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=money_manager_transactions.csv"}
    )

# --- WATCHLIST & MARKET DIP TRIGGERS ---
@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
def handle_watchlist():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'DELETE':
        item_id = request.args.get('id')
        ticker = request.args.get('ticker')
        if item_id:
            cursor.execute('DELETE FROM watchlist WHERE id = ?', (item_id,))
        elif ticker:
            cursor.execute('DELETE FROM watchlist WHERE ticker = ?', (ticker.strip().upper(),))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'POST':
        data = request.json or {}
        ticker = data.get('ticker', '').strip().upper()
        if not ticker:
            conn.close()
            return jsonify({'error': 'Ticker is required'}), 400
        target_dip_pct = float(data.get('target_dip_pct', 5.0))
        target_price = float(data.get('target_price', 0.0))
        notes = data.get('notes', '')

        cursor.execute('''
            INSERT INTO watchlist (ticker, target_dip_pct, target_price, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                target_dip_pct = excluded.target_dip_pct,
                target_price = excluded.target_price,
                notes = excluded.notes
        ''', (ticker, target_dip_pct, target_price, notes))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'ticker': ticker})

    # GET
    cursor.execute('SELECT * FROM watchlist ORDER BY created_at DESC')
    items = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute('SELECT stock_investment_budget FROM accounts WHERE id = 1')
    acc = cursor.fetchone()
    stock_budget = acc['stock_investment_budget'] if acc else 0.0
    conn.close()

    symbols = [item['ticker'] for item in items]
    quotes = fetch_multiple_quotes(symbols) if symbols else {}

    enriched_watchlist = []
    active_dip_alerts_count = 0

    for item in items:
        sym = item['ticker']
        quote = quotes.get(sym, {})
        current_price = quote.get('current_price', 0.0)
        year_high = quote.get('year_high', current_price)
        year_low = quote.get('year_low', current_price)
        dip_from_high = quote.get('dip_from_high_pct', 0.0)
        currency = quote.get('currency', 'AUD' if sym.endswith('.AX') else 'USD')

        target_dip = item['target_dip_pct']
        target_price = item['target_price']

        is_dip_triggered = (dip_from_high >= target_dip) or (target_price > 0 and current_price > 0 and current_price <= target_price)
        if is_dip_triggered:
            active_dip_alerts_count += 1

        suggested_buy_cash = round(stock_budget * 0.25, 2) if is_dip_triggered and stock_budget > 0 else 0.0

        enriched_watchlist.append({
            'id': item['id'],
            'ticker': sym,
            'current_price': current_price,
            'year_high': year_high,
            'year_low': year_low,
            'dip_from_high_pct': dip_from_high,
            'target_dip_pct': target_dip,
            'target_price': target_price,
            'is_dip_triggered': is_dip_triggered,
            'suggested_buy_cash': suggested_buy_cash,
            'currency': currency,
            'notes': item['notes']
        })

    return jsonify({
        'watchlist': enriched_watchlist,
        'stock_budget': stock_budget,
        'active_alerts': active_dip_alerts_count
    })

# --- 1-CLICK ETF PURCHASE ALLOCATOR ---
@app.route('/api/tools/allocate', methods=['POST'])
def allocate_purchases():
    data = request.json or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT stock_investment_budget FROM accounts WHERE id = 1')
    acc = cursor.fetchone()
    conn.close()

    budget = float(data.get('budget', acc['stock_investment_budget'] if acc else 0.0))
    targets = data.get('targets', [])

    if not targets:
        return jsonify({'error': 'No targets specified'}), 400

    symbols = [t['ticker'].strip().upper() for t in targets]
    quotes = fetch_multiple_quotes(symbols)
    aud_usd_rate = fetch_aud_usd_rate()

    plan = []
    total_spent = 0.0

    for t in targets:
        sym = t['ticker'].strip().upper()
        weight = float(t.get('weight_pct', 100.0 / len(targets)))
        allocated_cash = budget * (weight / 100.0)
        
        quote = quotes.get(sym, {})
        price = quote.get('current_price', 0.0)
        is_asx = sym.endswith('.AX')
        price_aud = price * (1.0 if is_asx else aud_usd_rate)

        if price_aud > 0:
            shares_to_buy = int(allocated_cash // price_aud)
            cost_aud = round(shares_to_buy * price_aud, 2)
        else:
            shares_to_buy = 0
            cost_aud = 0.0

        total_spent += cost_aud
        plan.append({
            'ticker': sym,
            'price': price,
            'price_aud': round(price_aud, 2),
            'weight_pct': weight,
            'allocated_cash': round(allocated_cash, 2),
            'shares_to_buy': shares_to_buy,
            'cost_aud': cost_aud,
            'currency': 'AUD' if is_asx else 'USD'
        })

    return jsonify({
        'total_budget': budget,
        'total_spent': round(total_spent, 2),
        'remaining_cash': round(budget - total_spent, 2),
        'allocation_plan': plan
    })

# --- ESTIMATED DIVIDEND TRACKER ---
@app.route('/api/tools/dividends', methods=['GET'])
def get_dividend_tracker():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ticker, shares, avg_cost FROM portfolio')
    holdings = [dict(row) for row in cursor.fetchall()]
    conn.close()

    symbols = [h['ticker'] for h in holdings]
    quotes = fetch_multiple_quotes(symbols) if symbols else {}
    actual_yields = fetch_multiple_dividend_yields(symbols) if symbols else {}
    aud_usd_rate = fetch_aud_usd_rate()

    total_annual_dividend_aud = 0.0
    dividend_items = []

    for h in holdings:
        sym = h['ticker']
        quote = quotes.get(sym, {})
        current_price = quote.get('current_price', h['avg_cost'])
        is_asx = sym.endswith('.AX')
        multiplier = 1.0 if is_asx else aud_usd_rate
        mkt_val_aud = h['shares'] * current_price * multiplier

        yield_pct = actual_yields.get(sym, 0.0)
        annual_div = round(mkt_val_aud * (yield_pct / 100.0), 2)
        monthly_div = round(annual_div / 12.0, 2)
        total_annual_dividend_aud += annual_div

        dividend_items.append({
            'ticker': sym,
            'shares': h['shares'],
            'market_value_aud': round(mkt_val_aud, 2),
            'yield_pct': yield_pct,
            'annual_dividend_aud': annual_div,
            'monthly_dividend_aud': monthly_div
        })

    return jsonify({
        'total_annual_dividends': round(total_annual_dividend_aud, 2),
        'total_monthly_dividends': round(total_annual_dividend_aud / 12.0, 2),
        'dividend_breakdown': dividend_items
    })

    return jsonify({
        'total_annual_dividends': round(total_annual_dividend_aud, 2),
        'total_monthly_dividends': round(total_annual_dividend_aud / 12.0, 2),
        'dividend_breakdown': dividend_items
    })

# --- NET WORTH MILESTONES ---
@app.route('/api/tools/milestones', methods=['GET'])
def get_milestones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT liquid_savings, spending_balance, stock_investment_budget FROM accounts WHERE id = 1')
    acc = cursor.fetchone()
    liquid_savings = acc['liquid_savings'] if acc else 0.0
    spending_balance = acc['spending_balance'] if acc else 0.0
    stock_budget = acc['stock_investment_budget'] if acc else 0.0

    cursor.execute('SELECT ticker, shares, avg_cost FROM portfolio')
    holdings = [dict(row) for row in cursor.fetchall()]
    conn.close()

    aud_usd_rate = fetch_aud_usd_rate()
    portfolio_value = sum(
        h['shares'] * STOCK_CACHE.get(h['ticker'], {}).get('current_price', h['avg_cost']) *
        (1.0 if h['ticker'].endswith('.AX') else aud_usd_rate)
        for h in holdings
    )
    current_net_worth = liquid_savings + spending_balance + stock_budget + portfolio_value

    TARGET_MILESTONES = [10000, 25000, 50000, 100000, 250000, 500000, 1000000]
    milestone_results = []

    for m_target in TARGET_MILESTONES:
        pct = min(100.0, round((current_net_worth / m_target) * 100.0, 1))
        gap = max(0.0, round(m_target - current_net_worth, 2))
        achieved = current_net_worth >= m_target

        milestone_results.append({
            'target': m_target,
            'achieved': achieved,
            'progress_pct': pct,
            'gap_remaining': gap
        })

    return jsonify({
        'current_net_worth': round(current_net_worth, 2),
        'milestones': milestone_results
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
