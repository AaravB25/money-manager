def calculate_compound_interest(initial_amount, monthly_contribution, annual_interest_rate, years, compounding_frequency=12):
    """
    Calculates compound interest trajectory over specified years.
    """
    initial_amount = max(0.0, float(initial_amount))
    monthly_contribution = max(0.0, float(monthly_contribution))
    annual_interest_rate = max(0.0, float(annual_interest_rate)) / 100.0
    years = max(1, int(years))
    
    months = years * 12
    monthly_rate = annual_interest_rate / 12.0
    
    labels = []
    future_values = []
    total_contributions = []
    total_interests = []
    
    current_value = initial_amount
    accumulated_contribution = initial_amount
    
    for m in range(0, months + 1):
        if m % 12 == 0:
            labels.append(f"Year {m // 12}")
            future_values.append(round(current_value, 2))
            total_contributions.append(round(accumulated_contribution, 2))
            total_interests.append(round(max(0.0, current_value - accumulated_contribution), 2))
            
        if m < months:
            current_value = (current_value + monthly_contribution) * (1 + monthly_rate)
            accumulated_contribution += monthly_contribution
            
    return {
        'years': years,
        'final_value': future_values[-1],
        'total_contributions': total_contributions[-1],
        'total_interest': total_interests[-1],
        'labels': labels,
        'future_values': future_values,
        'total_contributions_timeline': total_contributions,
        'total_interests_timeline': total_interests
    }

def calculate_personalized_net_worth_projection(current_savings, current_portfolio, current_spending, pay_amount, pay_frequency='fortnightly', spending_pct=10.0, savings_pct=40.0, stock_pct=50.0, stock_annual_return=8.0, savings_annual_return=4.0, years=30):
    """
    Projects total Net Worth over 1 to 30 years combining:
    - Current Liquid Savings ($306.34) + 40% pay additions at savings_annual_return%
    - Current Stock Portfolio (~$16,593 AUD) + 50% pay stock budget additions at stock_annual_return%
    - Current Spending Cash ($108.02)
    """
    pay_amount = max(0.0, float(pay_amount))
    stock_annual_return = max(0.0, float(stock_annual_return)) / 100.0
    savings_annual_return = max(0.0, float(savings_annual_return)) / 100.0
    
    # Frequency conversion to monthly
    periods_per_year = 26.0 if pay_frequency == 'fortnightly' else 52.0
    monthly_multiplier = periods_per_year / 12.0
    
    monthly_spending = (pay_amount * (spending_pct / 100.0)) * monthly_multiplier
    monthly_savings_addition = (pay_amount * (savings_pct / 100.0)) * monthly_multiplier
    monthly_stock_addition = (pay_amount * (stock_pct / 100.0)) * monthly_multiplier
    
    monthly_stock_rate = stock_annual_return / 12.0
    monthly_savings_rate = savings_annual_return / 12.0
    
    portfolio_val = max(0.0, float(current_portfolio))
    savings_val = max(0.0, float(current_savings))
    spending_val = max(0.0, float(current_spending))
    
    years = max(1, int(years))
    months = years * 12
    
    labels = []
    total_net_worth = []
    portfolio_projection = []
    savings_projection = []
    
    for m in range(0, months + 1):
        if m % 12 == 0:
            labels.append(f"Year {m // 12}")
            net_val = round(portfolio_val + savings_val + spending_val, 2)
            total_net_worth.append(net_val)
            portfolio_projection.append(round(portfolio_val, 2))
            savings_projection.append(round(savings_val, 2))
            
        if m < months:
            portfolio_val = (portfolio_val + monthly_stock_addition) * (1 + monthly_stock_rate)
            savings_val = (savings_val + monthly_savings_addition) * (1 + monthly_savings_rate)
            
    return {
        'years': years,
        'pay_amount': pay_amount,
        'pay_frequency': pay_frequency,
        'labels': labels,
        'net_worth': total_net_worth,
        'portfolio': portfolio_projection,
        'savings': savings_projection,
        'year_1_net_worth': total_net_worth[1] if len(total_net_worth) > 1 else total_net_worth[0],
        'year_5_net_worth': total_net_worth[5] if len(total_net_worth) > 5 else total_net_worth[-1],
        'year_10_net_worth': total_net_worth[10] if len(total_net_worth) > 10 else total_net_worth[-1],
        'final_net_worth': total_net_worth[-1]
    }

def calculate_wealth_plan(starting_state, events, config):
    """
    Month-by-month wealth simulation supporting life events.

    Event types:
      salary_change     - new_pay_amount
      property_buy      - price, deposit_pct, rate_pct, term_years, appreciation_pct,
                          rental_yield_pct, label
      property_sell     - property_id, override_price
      loan_refinance    - property_id, new_rate_pct
      lump_invest       - amount (savings -> portfolio)
      lump_sell         - amount (portfolio -> savings)
      major_expense     - amount, label
      split_change      - spending_pct, savings_pct, stock_pct
      career_break      - duration_months (pay pauses)
      windfall          - amount, source (e.g. inheritance, bonus)
    """
    years = max(1, int(config.get('years', 30)))
    total_months = years * 12

    pay_amount       = float(config.get('pay_amount', 950))
    pay_frequency    = config.get('pay_frequency', 'fortnightly')
    spending_pct     = float(config.get('spending_pct', 10))
    savings_pct      = float(config.get('savings_pct', 40))
    stock_pct        = float(config.get('stock_pct', 50))
    stock_return     = float(config.get('stock_annual_return', 8)) / 100
    savings_return   = float(config.get('savings_annual_return', 4)) / 100
    inflation_rate   = float(config.get('inflation_rate', 3)) / 100
    dividend_yield   = float(config.get('dividend_yield_pct', 2)) / 100
    super_pct        = float(config.get('employer_super_pct', 11.5)) / 100
    super_return     = float(config.get('super_annual_return', 7)) / 100

    periods_per_year = 26.0 if pay_frequency == 'fortnightly' else 52.0
    pays_per_month   = periods_per_year / 12.0

    savings_val  = float(starting_state.get('savings', 0))
    portfolio_val = float(starting_state.get('portfolio', 0))
    spending_val = float(starting_state.get('spending', 0))
    super_val    = float(starting_state.get('super_balance', 0))

    properties = []
    prop_id_counter = 0
    pay_paused_months_remaining = 0  # for career_break

    sorted_events = sorted(events, key=lambda e: (int(e.get('year', 0)), int(e.get('month', 1))))

    def events_at(month_idx):
        yr = month_idx // 12
        mo = (month_idx % 12) + 1
        return [e for e in sorted_events if int(e.get('year', 0)) == yr and int(e.get('month', 1)) == mo]

    labels = []
    net_worth_series      = []
    real_net_worth_series = []
    savings_series        = []
    portfolio_series      = []
    property_equity_series = []
    super_series          = []
    snapshot_table        = []

    monthly_stock_rate   = stock_return / 12
    monthly_savings_rate = savings_return / 12
    monthly_inflation    = inflation_rate / 12
    monthly_dividend     = dividend_yield / 12
    monthly_super_rate   = super_return / 12

    cumulative_inflation_factor = 1.0

    for m in range(total_months + 1):
        # --- Apply events ---
        for ev in events_at(m):
            etype = ev.get('type', '')

            if etype == 'salary_change':
                pay_amount = float(ev.get('new_pay_amount', pay_amount))

            elif etype == 'split_change':
                spending_pct = float(ev.get('spending_pct', spending_pct))
                savings_pct  = float(ev.get('savings_pct', savings_pct))
                stock_pct    = float(ev.get('stock_pct', stock_pct))

            elif etype == 'career_break':
                pay_paused_months_remaining = int(ev.get('duration_months', 6))

            elif etype == 'windfall':
                amount = float(ev.get('amount', 0))
                savings_val += amount

            elif etype == 'property_buy':
                price           = float(ev.get('price', 0))
                deposit_pct     = float(ev.get('deposit_pct', 20))
                rate_pct        = float(ev.get('rate_pct', 5.5))
                term_years      = int(ev.get('term_years', 30))
                appreciation_pct = float(ev.get('appreciation_pct', 5)) / 100
                rental_yield_pct = float(ev.get('rental_yield_pct', 0)) / 100
                label           = ev.get('label', f'Property {prop_id_counter + 1}')

                deposit = price * deposit_pct / 100
                loan    = price - deposit
                savings_val -= deposit
                savings_val  = max(0.0, savings_val)

                monthly_rate = (rate_pct / 100) / 12
                n = term_years * 12
                if monthly_rate > 0:
                    emi = loan * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
                else:
                    emi = loan / n if n > 0 else 0

                properties.append({
                    'id': prop_id_counter,
                    'label': label,
                    'current_value': price,
                    'loan_balance': loan,
                    'monthly_emi': round(emi, 2),
                    'monthly_loan_rate': monthly_rate,
                    'monthly_appreciation_rate': appreciation_pct / 12,
                    'monthly_rental_rate': rental_yield_pct / 12,
                    'months_remaining': n
                })
                prop_id_counter += 1

            elif etype == 'property_sell':
                pid = int(ev.get('property_id', -1))
                override_price = ev.get('override_price')
                for prop in list(properties):
                    if prop['id'] == pid:
                        sell_price = float(override_price) if override_price else prop['current_value']
                        equity = max(0.0, sell_price - prop['loan_balance'])
                        savings_val += equity
                        properties.remove(prop)
                        break

            elif etype == 'loan_refinance':
                pid          = int(ev.get('property_id', 0))
                new_rate_pct = float(ev.get('new_rate_pct', 5.0))
                for prop in properties:
                    if prop['id'] == pid:
                        new_monthly_rate = (new_rate_pct / 100) / 12
                        remaining_months = prop['months_remaining']
                        loan_bal = prop['loan_balance']
                        if new_monthly_rate > 0 and remaining_months > 0:
                            new_emi = loan_bal * (new_monthly_rate * (1 + new_monthly_rate) ** remaining_months) / \
                                      ((1 + new_monthly_rate) ** remaining_months - 1)
                        else:
                            new_emi = loan_bal / remaining_months if remaining_months > 0 else 0
                        prop['monthly_loan_rate'] = new_monthly_rate
                        prop['monthly_emi'] = round(new_emi, 2)
                        break

            elif etype == 'lump_invest':
                amount = float(ev.get('amount', 0))
                actual = min(amount, savings_val)
                savings_val   -= actual
                portfolio_val += actual

            elif etype == 'lump_sell':
                amount = float(ev.get('amount', 0))
                actual = min(amount, portfolio_val)
                portfolio_val -= actual
                savings_val   += actual

            elif etype == 'major_expense':
                amount = float(ev.get('amount', 0))
                savings_val -= amount
                savings_val  = max(0.0, savings_val)

        # --- Snapshot at year boundaries ---
        if m % 12 == 0:
            prop_equity = sum(max(0, p['current_value'] - p['loan_balance']) for p in properties)
            total_nw    = round(savings_val + portfolio_val + spending_val + prop_equity + super_val, 2)
            real_nw     = round(total_nw / cumulative_inflation_factor, 2)
            yr = m // 12
            labels.append(f'Year {yr}')
            net_worth_series.append(total_nw)
            real_net_worth_series.append(real_nw)
            savings_series.append(round(savings_val, 2))
            portfolio_series.append(round(portfolio_val, 2))
            property_equity_series.append(round(prop_equity, 2))
            super_series.append(round(super_val, 2))
            snapshot_table.append({
                'year': yr,
                'net_worth': total_nw,
                'real_net_worth': real_nw,
                'savings': round(savings_val, 2),
                'portfolio': round(portfolio_val, 2),
                'property_equity': round(prop_equity, 2),
                'super': round(super_val, 2),
                'pay': round(pay_amount, 2),
                'pay_paused': pay_paused_months_remaining > 0,
                'properties': [{'label': p['label'], 'value': round(p['current_value'], 2),
                                 'loan': round(p['loan_balance'], 2),
                                 'rental_monthly': round(p['current_value'] * p['monthly_rental_rate'], 2)}
                                for p in properties]
            })

        if m >= total_months:
            break

        # --- Monthly pay (skip if career break active) ---
        if pay_paused_months_remaining > 0:
            pay_paused_months_remaining -= 1
        else:
            monthly_pay = pay_amount * pays_per_month
            savings_val  += monthly_pay * (savings_pct / 100)
            spending_val += monthly_pay * (spending_pct / 100)
            portfolio_val += monthly_pay * (stock_pct / 100)
            # Employer super (on gross pay approximation)
            super_val += monthly_pay * super_pct

        # --- Returns ---
        portfolio_val = portfolio_val * (1 + monthly_stock_rate)
        savings_val   = savings_val * (1 + monthly_savings_rate)
        super_val     = super_val * (1 + monthly_super_rate)

        # --- Dividend reinvestment (adds to portfolio) ---
        portfolio_val += portfolio_val * monthly_dividend

        # --- Properties: EMI, rental income, appreciation ---
        for prop in properties:
            # Rental income -> savings
            rental_income = prop['current_value'] * prop['monthly_rental_rate']
            savings_val += rental_income

            # EMI deducted from savings
            if prop['months_remaining'] > 0:
                emi = prop['monthly_emi']
                interest_portion   = prop['loan_balance'] * prop['monthly_loan_rate']
                principal_portion  = max(0.0, emi - interest_portion)
                prop['loan_balance'] = max(0.0, prop['loan_balance'] - principal_portion)
                prop['months_remaining'] -= 1
                savings_val -= emi
                savings_val  = max(0.0, savings_val)

            # Appreciation
            prop['current_value'] *= (1 + prop['monthly_appreciation_rate'])

        # --- Inflation tracking ---
        cumulative_inflation_factor *= (1 + monthly_inflation)

    milestones = {}
    for yr in [1, 5, 10, 20, years]:
        idx = min(yr, len(net_worth_series) - 1)
        milestones[f'year_{yr}'] = net_worth_series[idx]

    return {
        'labels': labels,
        'net_worth': net_worth_series,
        'real_net_worth': real_net_worth_series,
        'savings': savings_series,
        'portfolio': portfolio_series,
        'property_equity': property_equity_series,
        'super': super_series,
        'milestones': milestones,
        'snapshot_table': snapshot_table,
        'final_net_worth': net_worth_series[-1] if net_worth_series else 0,
        'final_real_net_worth': real_net_worth_series[-1] if real_net_worth_series else 0
    }


