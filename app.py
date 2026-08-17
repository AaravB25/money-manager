from flask import Flask, render_template, request, jsonify, Response, send_file
import csv
import io
import os
import re
import time
import math
from datetime import datetime, date, timedelta
from db import init_db, get_db_connection, DB_PATH
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

# Common ASX/US tickers for autocomplete search
TICKER_DIRECTORY = [
    'CBA.AX', 'WBC.AX', 'NAB.AX', 'ANZ.AX', 'BHP.AX', 'CSL.AX', 'RIO.AX', 'FMG.AX',
    'WES.AX', 'WOW.AX', 'TLS.AX', 'MQG.AX', 'ALL.AX', 'COL.AX', 'GMG.AX', 'TCL.AX',
    'VAS.AX', 'VHY.AX', 'IVV.AX', 'NDQ.AX', 'DHHF.AX', 'VAE.AX', 'XMET.AX', 'A200.AX',
    'VDHG.AX', 'IOZ.AX', 'VGS.AX', 'QUAL.AX', 'HACK.AX', 'ETHI.AX', 'MVW.AX',
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'INTC',
    'JPM', 'V', 'MA', 'DIS', 'NFLX', 'PYPL', 'SQ', 'COIN', 'PLTR', 'SOFI',
    'SPY', 'QQQ', 'VOO', 'VTI', 'ARKK', 'GPRO', 'GME', 'AMC', 'RIVN',
]

STOCK_CACHE = {}

@app.before_request
def setup_database():
    init_db()

@app.route('/')
def index():
    build_ts = int(time.time())
    return render_template('index.html', build_ts=build_ts)

# ============================================================
#  HELPER: compute net worth from DB
# ============================================================
def _compute_net_worth(cursor):
    """Returns (liquid_savings, spending, stock_budget, portfolio_value_aud, net_worth)."""
    cursor.execute("SELECT liquid_savings, spending_balance, stock_investment_budget FROM accounts WHERE id = 1")
    acc = cursor.fetchone()
    liquid_savings = acc['liquid_savings'] if acc else 0.0
    spending = acc['spending_balance'] if acc else 0.0
    stock_budget = acc['stock_investment_budget'] if acc else 0.0

    cursor.execute("SELECT ticker, shares, avg_cost FROM portfolio")
    holdings = [dict(row) for row in cursor.fetchall()]
    aud_usd_rate = fetch_aud_usd_rate()
    portfolio_value = sum(
        h['shares'] * STOCK_CACHE.get(h['ticker'], {}).get('current_price', h['avg_cost']) *
        (1.0 if h['ticker'].endswith('.AX') else aud_usd_rate)
        for h in holdings
    )
    net_worth = liquid_savings + spending + stock_budget + portfolio_value
    return liquid_savings, spending, stock_budget, portfolio_value, net_worth

# ============================================================
#  DASHBOARD
# ============================================================
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

# ============================================================
#  NET WORTH SNAPSHOTS
# ============================================================
@app.route('/api/snapshots', methods=['GET', 'POST'])
def handle_snapshots():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        today_str = date.today().isoformat()
        ls, sp, sb, pv, nw = _compute_net_worth(cursor)
        cursor.execute('''
            INSERT OR REPLACE INTO net_worth_snapshots (date, net_worth, liquid_savings, spending_balance, stock_budget, portfolio_value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (today_str, round(nw, 2), round(ls, 2), round(sp, 2), round(sb, 2), round(pv, 2)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'date': today_str, 'net_worth': round(nw, 2)})

    # GET - return last 90 snapshots
    days = request.args.get('days', 90, type=int)
    cursor.execute('SELECT * FROM net_worth_snapshots ORDER BY date DESC LIMIT ?', (days,))
    snapshots = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'snapshots': list(reversed(snapshots))})

# ============================================================
#  MONTHLY CASHFLOW (income vs expenses)
# ============================================================
@app.route('/api/cashflow/monthly', methods=['GET'])
def monthly_cashflow():
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()
    month_start = now.replace(day=1).strftime('%Y-%m-%d 00:00:00')

    cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM income_logs WHERE date >= ?", (month_start,))
    income_total = cursor.fetchone()['total']

    cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ?", (month_start,))
    expense_total = cursor.fetchone()['total']

    savings_rate = round(((income_total - expense_total) / income_total * 100), 1) if income_total > 0 else 0.0

    conn.close()
    return jsonify({
        'month': now.strftime('%B %Y'),
        'income_total': round(income_total, 2),
        'expense_total': round(expense_total, 2),
        'net_cashflow': round(income_total - expense_total, 2),
        'savings_rate': savings_rate
    })

# ============================================================
#  SPENDING CATEGORIES BREAKDOWN
# ============================================================
@app.route('/api/cashflow/categories', methods=['GET'])
def spending_categories():
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()
    month_start = now.replace(day=1).strftime('%Y-%m-%d 00:00:00')

    cursor.execute("""
        SELECT COALESCE(category, 'General') as cat, SUM(amount) as total
        FROM expenses WHERE date >= ?
        GROUP BY cat ORDER BY total DESC
    """, (month_start,))
    rows = cursor.fetchall()
    conn.close()

    categories = [{'category': r['cat'], 'total': round(r['total'], 2)} for r in rows]
    return jsonify({'categories': categories, 'month': now.strftime('%B %Y')})

# ============================================================
#  USER SETTINGS
# ============================================================
@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        fields = []
        values = []
        for key in ['pay_cycle', 'pay_day', 'last_paycheck_date', 'spending_threshold', 'theme']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(1)
            cursor.execute(f"UPDATE user_settings SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
        conn.close()
        return jsonify({'success': True})

    cursor.execute("SELECT * FROM user_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'pay_cycle': 'fortnightly', 'pay_day': 4, 'spending_threshold': 100.0, 'theme': 'dark'})

# ============================================================
#  PAY CYCLE COUNTDOWN
# ============================================================
@app.route('/api/pay-countdown', methods=['GET'])
def pay_countdown():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pay_cycle, pay_day, last_paycheck_date FROM user_settings WHERE id = 1")
    s = cursor.fetchone()

    # Also check the last income log date
    cursor.execute("SELECT date FROM income_logs ORDER BY date DESC LIMIT 1")
    last_income = cursor.fetchone()
    conn.close()

    if not s:
        return jsonify({'days_remaining': -1, 'next_pay_date': ''})

    pay_cycle = s['pay_cycle'] or 'fortnightly'
    last_pay = s['last_paycheck_date'] or ''

    # Use income log date if no explicit last paycheck
    if not last_pay and last_income:
        last_pay = last_income['date'][:10] if last_income['date'] else ''

    if not last_pay:
        return jsonify({'days_remaining': -1, 'next_pay_date': '', 'message': 'Log a paycheck to start countdown'})

    try:
        last_dt = datetime.strptime(last_pay[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'days_remaining': -1, 'next_pay_date': ''})

    cycle_days = {'weekly': 7, 'fortnightly': 14, 'monthly': 30}.get(pay_cycle, 14)
    next_pay = last_dt + timedelta(days=cycle_days)
    today = date.today()

    while next_pay <= today:
        next_pay += timedelta(days=cycle_days)

    days_remaining = (next_pay - today).days

    return jsonify({
        'days_remaining': days_remaining,
        'next_pay_date': next_pay.isoformat(),
        'pay_cycle': pay_cycle
    })

# ============================================================
#  PORTFOLIO
# ============================================================
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT ticker, shares, avg_cost, updated_at FROM portfolio ORDER BY ticker ASC")
    holdings = [dict(row) for row in cursor.fetchall()]

    # Get target allocations
    cursor.execute("SELECT ticker, target_pct FROM target_allocations")
    targets = {r['ticker']: r['target_pct'] for r in cursor.fetchall()}

    # Get total brokerage fees
    cursor.execute("SELECT COALESCE(SUM(fee_amount), 0) as total_fees FROM brokerage_fees")
    total_brokerage = cursor.fetchone()['total_fees']

    symbols = [h['ticker'] for h in holdings]
    if symbols:
        quotes = fetch_multiple_quotes(symbols)
        STOCK_CACHE.update(quotes)

    aud_usd_rate = fetch_aud_usd_rate()

    enriched = []
    total_val_aud = 0.0
    total_cost_aud = 0.0
    max_holding_pct = 0.0
    max_holding_ticker = ''

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

        # Break-even price: avg_cost in native currency
        break_even = h['avg_cost']

        # Annualised return (CAGR)
        first_date = h.get('updated_at', '')
        cagr = 0.0
        # Use a simple estimate: days since first update
        try:
            if first_date:
                first_dt = datetime.strptime(first_date[:10], '%Y-%m-%d')
                days_held = max(1, (datetime.now() - first_dt).days)
                years_held = days_held / 365.25
                if native_cost_basis > 0 and years_held > 0:
                    total_return_ratio = native_mkt_val / native_cost_basis
                    if total_return_ratio > 0:
                        cagr = round((math.pow(total_return_ratio, 1.0 / years_held) - 1) * 100, 2)
        except Exception:
            pass

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
            'break_even': break_even,
            'cagr': cagr,
            'market_value_native': native_mkt_val,
            'cost_basis_native': native_cost_basis,
            'gain_loss_native': native_gain_loss,
            'market_value_aud': aud_mkt_val,
            'cost_basis_aud': aud_cost_basis,
            'gain_loss_aud': aud_gain_loss,
            'gain_loss_pct': gain_loss_pct,
            'daily_change': change,
            'daily_change_pct': change_pct,
            'currency': currency,
            'target_pct': targets.get(sym, None)
        })

    # Concentration analysis
    concentration_warnings = []
    for item in enriched:
        if total_val_aud > 0:
            pct_of_portfolio = round((item['market_value_aud'] / total_val_aud) * 100, 1)
            item['portfolio_weight_pct'] = pct_of_portfolio
            if pct_of_portfolio > max_holding_pct:
                max_holding_pct = pct_of_portfolio
                max_holding_ticker = item['code']
            if pct_of_portfolio > 30:
                concentration_warnings.append({
                    'ticker': item['code'],
                    'weight': pct_of_portfolio,
                    'message': f'{item["code"]} is {pct_of_portfolio}% of portfolio - consider rebalancing'
                })
            # Target allocation drift
            if item['target_pct'] is not None:
                item['allocation_drift'] = round(pct_of_portfolio - item['target_pct'], 1)
        else:
            item['portfolio_weight_pct'] = 0.0

    conn.close()

    total_gain_loss_aud = round(total_val_aud - total_cost_aud, 2)
    total_gain_loss_pct = round((total_gain_loss_aud / total_cost_aud * 100), 2) if total_cost_aud > 0 else 0.0

    return jsonify({
        'holdings': enriched,
        'total_value_aud': round(total_val_aud, 2),
        'total_cost_aud': round(total_cost_aud, 2),
        'total_gain_loss_aud': total_gain_loss_aud,
        'total_gain_loss_pct': total_gain_loss_pct,
        'aud_usd_rate': aud_usd_rate,
        'concentration_warnings': concentration_warnings,
        'total_brokerage_fees': round(total_brokerage, 2)
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

@app.route('/api/portfolio/search', methods=['GET'])
def search_tickers():
    q = request.args.get('q', '').strip().upper()
    if len(q) < 1:
        return jsonify({'results': []})
    matches = [t for t in TICKER_DIRECTORY if q in t]
    enriched = []
    for t in matches[:15]:
        name = STOCK_NAMES.get(t, t.replace('.AX', ''))
        enriched.append({'ticker': t, 'name': name})
    return jsonify({'results': enriched})

# ============================================================
#  TARGET ALLOCATIONS
# ============================================================
@app.route('/api/allocations', methods=['GET', 'POST', 'DELETE'])
def handle_allocations():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'DELETE':
        alloc_id = request.args.get('id')
        ticker = request.args.get('ticker')
        if alloc_id:
            cursor.execute('DELETE FROM target_allocations WHERE id = ?', (alloc_id,))
        elif ticker:
            cursor.execute('DELETE FROM target_allocations WHERE ticker = ?', (ticker.strip().upper(),))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'POST':
        data = request.json or {}
        ticker = data.get('ticker', '').strip().upper()
        target_pct = float(data.get('target_pct', 10.0))
        if not ticker:
            conn.close()
            return jsonify({'error': 'Ticker required'}), 400
        cursor.execute('''
            INSERT INTO target_allocations (ticker, target_pct) VALUES (?, ?)
            ON CONFLICT(ticker) DO UPDATE SET target_pct = excluded.target_pct
        ''', (ticker, target_pct))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'ticker': ticker, 'target_pct': target_pct})

    cursor.execute('SELECT * FROM target_allocations ORDER BY ticker')
    allocs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'allocations': allocs})

# ============================================================
#  BROKERAGE FEES
# ============================================================
@app.route('/api/brokerage', methods=['GET', 'POST'])
def handle_brokerage():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        ticker = data.get('ticker', '').strip().upper()
        action = data.get('action', 'BUY').upper()
        fee = float(data.get('fee_amount', 0.0))
        trade_amt = float(data.get('trade_amount', 0.0))
        cursor.execute('''
            INSERT INTO brokerage_fees (ticker, action, fee_amount, trade_amount) VALUES (?, ?, ?, ?)
        ''', (ticker, action, fee, trade_amt))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    cursor.execute('SELECT * FROM brokerage_fees ORDER BY date DESC LIMIT 50')
    fees = [dict(r) for r in cursor.fetchall()]
    cursor.execute('SELECT COALESCE(SUM(fee_amount), 0) as total FROM brokerage_fees')
    total = cursor.fetchone()['total']
    conn.close()
    return jsonify({'fees': fees, 'total_brokerage': round(total, 2)})

# ============================================================
#  TRADE
# ============================================================
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

# ============================================================
#  INCOME
# ============================================================
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
        INSERT INTO income_logs (description, amount, spending_amount, savings_amount, stock_allocation, income_type)
        VALUES (?, ?, ?, ?, ?, 'paycheck')
    ''', (description, split['pay_amount'], split['spending_amount'], split['savings_amount'], split['stock_allocation']))

    cursor.execute('''
        UPDATE accounts
        SET liquid_savings = liquid_savings + ?,
            spending_balance = spending_balance + ?,
            stock_investment_budget = stock_investment_budget + ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (split['savings_amount'], split['spending_amount'], split['active_stock_allocation']))

    # Update last paycheck date
    cursor.execute("UPDATE user_settings SET last_paycheck_date = ? WHERE id = 1", (date.today().isoformat(),))

    audit_desc = f"[INCOME] {description}: ${amount:.2f} | Spending: +${split['spending_amount']:.2f} | Savings: +${split['savings_amount']:.2f} | Stock Budget: +${split['active_stock_allocation']:.2f}"
    cursor.execute('''
        INSERT INTO transactions (type, amount, description)
        VALUES ('INCOME', ?, ?)
    ''', (amount, audit_desc))
    income_tx_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Income of ${amount:.2f} recorded.', 'split': split, 'transaction_id': income_tx_id})

# ============================================================
#  SIDE INCOME (non-paycheck)
# ============================================================
@app.route('/api/side-income', methods=['POST'])
def add_side_income():
    data = request.json or {}
    description = data.get('description', 'Side Income').strip()
    try:
        amount = float(data.get('amount', 0.0))
    except ValueError:
        return jsonify({'error': 'Invalid amount'}), 400
    if amount <= 0:
        return jsonify({'error': 'Amount must be > 0'}), 400

    destination = data.get('destination', 'savings')

    conn = get_db_connection()
    cursor = conn.cursor()

    col_map = {'savings': 'liquid_savings', 'spending': 'spending_balance', 'stock_budget': 'stock_investment_budget'}
    col = col_map.get(destination, 'liquid_savings')

    cursor.execute(f"UPDATE accounts SET {col} = {col} + ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (amount,))

    cursor.execute('''
        INSERT INTO income_logs (description, amount, spending_amount, savings_amount, stock_allocation, income_type)
        VALUES (?, ?, 0, ?, 0, 'side_income')
    ''', (description, amount, amount if destination == 'savings' else 0))

    audit_desc = f"[SIDE INCOME] {description}: ${amount:.2f} -> {destination}"
    cursor.execute("INSERT INTO transactions (type, amount, description) VALUES ('INCOME', ?, ?)", (amount, audit_desc))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'Side income of ${amount:.2f} recorded to {destination}.'})

# ============================================================
#  INCOME HISTORY
# ============================================================
@app.route('/api/income/history', methods=['GET'])
def income_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    income_type = request.args.get('type', '')
    if income_type:
        cursor.execute("SELECT * FROM income_logs WHERE income_type = ? ORDER BY date DESC LIMIT 100", (income_type,))
    else:
        cursor.execute("SELECT * FROM income_logs ORDER BY date DESC LIMIT 100")
    logs = [dict(r) for r in cursor.fetchall()]

    # YTD totals
    year_start = f"{datetime.now().year}-01-01 00:00:00"
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as ytd FROM income_logs WHERE date >= ?", (year_start,))
    ytd = cursor.fetchone()['ytd']

    cursor.execute("SELECT COALESCE(SUM(amount), 0) as ytd_paycheck FROM income_logs WHERE date >= ? AND income_type = 'paycheck'", (year_start,))
    ytd_paycheck = cursor.fetchone()['ytd_paycheck']

    cursor.execute("SELECT COALESCE(SUM(amount), 0) as ytd_side FROM income_logs WHERE date >= ? AND income_type = 'side_income'", (year_start,))
    ytd_side = cursor.fetchone()['ytd_side']

    conn.close()
    return jsonify({
        'income_logs': logs,
        'ytd_total': round(ytd, 2),
        'ytd_paycheck': round(ytd_paycheck, 2),
        'ytd_side_income': round(ytd_side, 2)
    })

# ============================================================
#  AUSTRALIAN TAX ESTIMATE
# ============================================================
@app.route('/api/tax-estimate', methods=['GET'])
def tax_estimate():
    conn = get_db_connection()
    cursor = conn.cursor()

    year_start = f"{datetime.now().year}-01-01 00:00:00"
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as ytd FROM income_logs WHERE date >= ?", (year_start,))
    ytd_income = cursor.fetchone()['ytd']

    # Project annual income
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    projected_annual = round(ytd_income * (365.0 / max(day_of_year, 1)), 2)

    # AUS 2024-25 marginal tax rates (resident)
    brackets = [
        (18200, 0),
        (45000, 0.16),
        (135000, 0.30),
        (190000, 0.37),
        (float('inf'), 0.45)
    ]

    tax = 0.0
    prev_threshold = 0
    remaining = projected_annual
    bracket_info = []

    for threshold, rate in brackets:
        taxable_in_bracket = min(remaining, threshold - prev_threshold)
        if taxable_in_bracket <= 0:
            break
        tax_in_bracket = taxable_in_bracket * rate
        tax += tax_in_bracket
        bracket_info.append({
            'range': f"${prev_threshold:,.0f} - ${threshold:,.0f}" if threshold < float('inf') else f"${prev_threshold:,.0f}+",
            'rate': f"{rate * 100:.0f}%",
            'taxable_amount': round(taxable_in_bracket, 2),
            'tax': round(tax_in_bracket, 2)
        })
        remaining -= taxable_in_bracket
        prev_threshold = threshold

    effective_rate = round((tax / projected_annual * 100), 1) if projected_annual > 0 else 0.0

    conn.close()
    return jsonify({
        'ytd_income': round(ytd_income, 2),
        'projected_annual': projected_annual,
        'estimated_tax': round(tax, 2),
        'effective_rate': effective_rate,
        'brackets': bracket_info
    })

# ============================================================
#  EXPENSES
# ============================================================
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
    category = data.get('category', 'General')
    notes = data.get('notes', '')

    result = quick_deduct_spending(amount, description, category, notes)
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

@app.route('/api/expenses/history', methods=['GET'])
def expense_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    limit = request.args.get('limit', 50, type=int)

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if search:
        query += " AND description LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to + ' 23:59:59')

    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    expenses = [dict(r) for r in cursor.fetchall()]

    # Weekly spending pace
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as weekly FROM expenses WHERE date >= ?", (week_start,))
    weekly_spent = cursor.fetchone()['weekly']

    conn.close()
    return jsonify({
        'expenses': expenses,
        'weekly_spent': round(weekly_spent, 2)
    })

# ============================================================
#  RECURRING EXPENSES
# ============================================================
@app.route('/api/recurring', methods=['GET', 'POST', 'DELETE'])
def handle_recurring():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'DELETE':
        rec_id = request.args.get('id')
        if rec_id:
            cursor.execute('DELETE FROM recurring_expenses WHERE id = ?', (rec_id,))
            conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'POST':
        data = request.json or {}
        desc = data.get('description', '').strip()
        amount = float(data.get('amount', 0.0))
        category = data.get('category', 'Bills')
        frequency = data.get('frequency', 'monthly')
        day_of_month = int(data.get('day_of_month', 1))

        if not desc or amount <= 0:
            conn.close()
            return jsonify({'error': 'Description and positive amount required'}), 400

        cursor.execute('''
            INSERT INTO recurring_expenses (description, amount, category, frequency, day_of_month)
            VALUES (?, ?, ?, ?, ?)
        ''', (desc, amount, category, frequency, day_of_month))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    # GET
    cursor.execute('SELECT * FROM recurring_expenses WHERE active = 1 ORDER BY day_of_month')
    items = [dict(r) for r in cursor.fetchall()]
    monthly_total = sum(i['amount'] for i in items)
    conn.close()
    return jsonify({'recurring': items, 'monthly_total': round(monthly_total, 2)})

@app.route('/api/recurring/<int:rec_id>/trigger', methods=['POST'])
def trigger_recurring(rec_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM recurring_expenses WHERE id = ?', (rec_id,))
    rec = cursor.fetchone()
    if not rec:
        conn.close()
        return jsonify({'error': 'Not found'}), 404

    amount = rec['amount']
    desc = rec['description']
    category = rec['category']

    # Deduct from spending balance
    cursor.execute("SELECT spending_balance FROM accounts WHERE id = 1")
    acc = cursor.fetchone()
    if acc['spending_balance'] < amount:
        conn.close()
        return jsonify({'error': f'Insufficient spending balance for ${amount:.2f}'}), 400

    cursor.execute("UPDATE accounts SET spending_balance = spending_balance - ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (amount,))
    cursor.execute('''
        INSERT INTO expenses (account_type, expense_type, amount, description, category)
        VALUES ('spending', 'recurring', ?, ?, ?)
    ''', (amount, f"[RECURRING] {desc}", category))
    cursor.execute('''
        INSERT INTO transactions (type, amount, description) VALUES ('EXPENSE', ?, ?)
    ''', (amount, f"[RECURRING EXPENSE] {desc}: -${amount:.2f}"))
    cursor.execute("UPDATE recurring_expenses SET last_triggered = ? WHERE id = ?", (date.today().isoformat(), rec_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'Recurring expense "{desc}" triggered: -${amount:.2f}'})

# ============================================================
#  TRANSFERS
# ============================================================
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

# ============================================================
#  UNDO TRANSACTION
# ============================================================
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
        desc = tx['description']
        amount = abs(tx['amount'])
        if '[SIDE INCOME]' in desc:
            if '-> spending' in desc:
                cursor.execute("UPDATE accounts SET spending_balance = MAX(0, spending_balance - ?), updated_at = CURRENT_TIMESTAMP WHERE id = 1", (amount,))
            elif '-> stock_budget' in desc:
                cursor.execute("UPDATE accounts SET stock_investment_budget = MAX(0, stock_investment_budget - ?), updated_at = CURRENT_TIMESTAMP WHERE id = 1", (amount,))
            else:
                cursor.execute("UPDATE accounts SET liquid_savings = MAX(0, liquid_savings - ?), updated_at = CURRENT_TIMESTAMP WHERE id = 1", (amount,))
        else:
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

        # Delete corresponding income_logs entry so Monthly Cashflow, YTD, and Tax estimates update
        cursor.execute('''
            DELETE FROM income_logs 
            WHERE id = (
                SELECT id FROM income_logs 
                WHERE amount = ? 
                ORDER BY ABS(strftime('%s', date) - strftime('%s', ?)) ASC 
                LIMIT 1
            )
        ''', (amount, tx['date']))

    elif tx_type == 'EXPENSE':
        amount = abs(tx['amount'])
        cursor.execute('''
            UPDATE accounts SET spending_balance = spending_balance + ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1
        ''', (amount,))

        # Delete corresponding expenses entry so Monthly Cashflow and category totals update
        cursor.execute('''
            DELETE FROM expenses 
            WHERE id = (
                SELECT id FROM expenses 
                WHERE amount = ? 
                ORDER BY ABS(strftime('%s', date) - strftime('%s', ?)) ASC 
                LIMIT 1
            )
        ''', (amount, tx['date']))

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

# ============================================================
#  TRANSACTIONS
# ============================================================
@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    limit = request.args.get('limit', 100, type=int)
    search = request.args.get('search', '')
    if search:
        cursor.execute('SELECT * FROM transactions WHERE description LIKE ? ORDER BY date DESC LIMIT ?', (f'%{search}%', limit))
    else:
        cursor.execute('SELECT * FROM transactions ORDER BY date DESC LIMIT ?', (limit,))
    txs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'transactions': txs})

# ============================================================
#  GOALS
# ============================================================
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
        target_date = data.get('target_date', '')
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
            INSERT INTO goals (title, target_amount, current_amount, category, linked_account, target_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, target, current, category, linked_account, target_date))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Goal "{title}" created successfully.'})

    # GET: resolve live balances for linked goals
    ls, sp, sb, pv, nw = _compute_net_worth(cursor)

    ACCOUNT_VALUES = {
        'savings': ls,
        'spending': sp,
        'stock_budget': sb,
        'portfolio': pv,
        'net_worth': nw,
        'none': None
    }

    cursor.execute('SELECT * FROM goals ORDER BY created_at DESC')
    raw_goals = [dict(row) for row in cursor.fetchall()]

    # Compute monthly savings rate for contribution suggestions
    now = datetime.now()
    month_start = now.replace(day=1).strftime('%Y-%m-%d 00:00:00')
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as monthly_income FROM income_logs WHERE date >= ?", (month_start,))
    monthly_income = cursor.fetchone()['monthly_income']

    conn.close()

    goals = []
    for g in raw_goals:
        linked = g.get('linked_account', 'none') or 'none'
        if linked != 'none' and linked in ACCOUNT_VALUES:
            g['current_amount'] = round(ACCOUNT_VALUES[linked], 2)
            g['live_linked'] = True
        else:
            g['live_linked'] = False

        # Deadline info
        target_date = g.get('target_date', '')
        remaining_amount = max(0, g['target_amount'] - g['current_amount'])

        if target_date:
            try:
                target_dt = datetime.strptime(target_date[:10], '%Y-%m-%d').date()
                days_remaining = (target_dt - date.today()).days
                g['days_remaining'] = max(0, days_remaining)
                weeks_remaining = max(1, days_remaining / 7)
                g['weekly_contribution_needed'] = round(remaining_amount / weeks_remaining, 2) if remaining_amount > 0 else 0.0
            except (ValueError, TypeError):
                g['days_remaining'] = None
                g['weekly_contribution_needed'] = None
        else:
            g['days_remaining'] = None
            g['weekly_contribution_needed'] = None

        # Projected completion based on monthly savings
        if monthly_income > 0 and remaining_amount > 0:
            months_to_goal = math.ceil(remaining_amount / (monthly_income * 0.4))  # 40% goes to savings
            projected_date = (date.today() + timedelta(days=months_to_goal * 30)).isoformat()
            g['projected_completion'] = projected_date
            g['months_to_goal'] = months_to_goal
        else:
            g['projected_completion'] = None
            g['months_to_goal'] = None

        goals.append(g)

    return jsonify({'goals': goals})

# ============================================================
#  SIMULATIONS
# ============================================================
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

# ============================================================
#  WATCHLIST
# ============================================================
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
        target_price_val = item['target_price']

        is_dip_triggered = (dip_from_high >= target_dip) or (target_price_val > 0 and current_price > 0 and current_price <= target_price_val)
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
            'target_price': target_price_val,
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

# ============================================================
#  DIVIDEND TRACKER
# ============================================================
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

# ============================================================
#  NET WORTH MILESTONES
# ============================================================
@app.route('/api/tools/milestones', methods=['GET'])
def get_milestones():
    conn = get_db_connection()
    cursor = conn.cursor()
    _, _, _, _, current_net_worth = _compute_net_worth(cursor)
    conn.close()

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

# ============================================================
#  EXPORT CSV
# ============================================================
@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    export_type = request.args.get('type', 'transactions')
    conn = get_db_connection()
    cursor = conn.cursor()
    output = io.StringIO()
    writer = csv.writer(output)

    if export_type == 'transactions':
        cursor.execute("SELECT id, type, ticker, shares, price, amount, description, date FROM transactions ORDER BY date DESC")
        writer.writerow(['ID', 'Type', 'Ticker', 'Shares', 'Price', 'Amount', 'Description', 'Date'])
        for r in cursor.fetchall():
            writer.writerow([r['id'], r['type'], r['ticker'] or '', r['shares'] or '', r['price'] or '', r['amount'], r['description'], r['date']])

    elif export_type == 'portfolio':
        cursor.execute("SELECT ticker, shares, avg_cost, updated_at FROM portfolio ORDER BY ticker")
        writer.writerow(['Ticker', 'Shares', 'Avg Cost', 'Last Updated'])
        for r in cursor.fetchall():
            writer.writerow([r['ticker'], r['shares'], r['avg_cost'], r['updated_at']])

    elif export_type == 'income':
        cursor.execute("SELECT * FROM income_logs ORDER BY date DESC")
        writer.writerow(['ID', 'Description', 'Amount', 'Spending', 'Savings', 'Stock Allocation', 'Type', 'Date'])
        for r in cursor.fetchall():
            r = dict(r)
            writer.writerow([r['id'], r['description'], r['amount'], r['spending_amount'], r['savings_amount'], r['stock_allocation'], r.get('income_type', 'paycheck'), r['date']])

    elif export_type == 'expenses':
        cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
        writer.writerow(['ID', 'Account Type', 'Expense Type', 'Amount', 'Description', 'Category', 'Date'])
        for r in cursor.fetchall():
            r = dict(r)
            writer.writerow([r['id'], r['account_type'], r['expense_type'], r['amount'], r['description'], r.get('category', 'General'), r['date']])

    conn.close()
    filename = f"money_manager_{export_type}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

# Keep legacy /api/export route working
@app.route('/api/export', methods=['GET'])
def export_csv_legacy():
    return export_csv()

# ============================================================
#  BACKUP (download full DB)
# ============================================================
@app.route('/api/backup', methods=['GET'])
def backup_db():
    if os.path.exists(DB_PATH):
        return send_file(DB_PATH, as_attachment=True, download_name='money_manager_backup.db')
    return jsonify({'error': 'Database file not found'}), 404

# ============================================================
#  WEEKLY SPENDING PACE
# ============================================================
@app.route('/api/spending/pace', methods=['GET'])
def spending_pace():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT spending_balance FROM accounts WHERE id = 1")
    acc = cursor.fetchone()
    balance = acc['spending_balance'] if acc else 0.0

    cursor.execute("SELECT spending_threshold FROM user_settings WHERE id = 1")
    s = cursor.fetchone()
    threshold = s['spending_threshold'] if s else 100.0

    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as weekly FROM expenses WHERE date >= ? AND account_type = 'spending'", (week_start,))
    weekly_spent = cursor.fetchone()['weekly']

    days_left_in_week = 7 - today.weekday()
    daily_pace = round(weekly_spent / max(1, today.weekday() + 1), 2)
    projected_weekly = round(daily_pace * 7, 2)

    conn.close()
    return jsonify({
        'weekly_spent': round(weekly_spent, 2),
        'spending_balance': round(balance, 2),
        'spending_threshold': threshold,
        'below_threshold': balance < threshold,
        'daily_pace': daily_pace,
        'projected_weekly': projected_weekly,
        'days_left_in_week': days_left_in_week
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
