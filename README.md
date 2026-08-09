# Money Manager - Personal Wealth & Portfolio Dashboard

A web-based personal finance, wealth simulation, and portfolio management dashboard built with Flask, Vanilla JS, CSS, and Chart.js.

## Features

- **Overview Dashboard**: Net worth breakdown, liquid savings, stock portfolio, spending cash, and stock target budget.
- **Paycheck Splitter**: Automatically splits income into Spending (10%), Liquid Savings (40%), and Stock Investment Budget (50%).
- **Stock Portfolio Tracker**: Real-time market prices via `yfinance` supporting ASX and US market assets.
- **Goals & Milestone Tracker**: Define custom goals or link directly to live balances (Savings, Portfolio, Net Worth, etc.).
- **Projections & Compound Calculator**: Long-term net worth compound trajectory modeling.
- **Life Timeline Wealth Planner**: Simulate future wealth considering salary growth, real estate purchases (with mortgage EMI & rental yield), career breaks, refinancing, lump-sum investments, and inflation adjustments.
- **Transaction Audit Log & CSV Export**: Export complete transaction log to CSV.

## Quick Start

### 1. Clone & Install Dependencies

```bash
git clone <your-repository-url>
cd money-manager
pip install -r requirements.txt
```

### 2. Seed Demo Data

To seed the local SQLite database with initial sample demo data (no personal financial info):

```bash
python seed_demo_data.py
```

### 3. Launch Application

```bash
python run.py
```

Open your browser and navigate to `http://127.0.0.1:5000`.

## Privacy & Security Note

- The SQLite database file (`money_manager.db`) and local environment files are included in `.gitignore` to prevent committing personal financial data.
- Never commit your personal `money_manager.db` to public repositories.

## License

MIT
