def calculate_pay_split(pay_amount, spending_pct=10.0, savings_pct=40.0, stock_pct=50.0, dip_fund_pct_of_stock=20.0):
    """
    Calculates the exact breakdown of an incoming pay amount:
    - 10% to Spending Account
    - 40% to Liquid Savings Account
    - 50% to Stock Investment Budget Total:
        * 80% of Stock Budget (40% total pay) -> Active Stock Buying Budget
        * 20% of Stock Budget (10% total pay) -> Market Dip Reserve Fund
    """
    if pay_amount <= 0:
        return {
            'pay_amount': 0.0,
            'spending_amount': 0.0,
            'savings_amount': 0.0,
            'stock_allocation': 0.0,
            'active_stock_allocation': 0.0,
            'dip_fund_allocation': 0.0,
            'spending_pct': spending_pct,
            'savings_pct': savings_pct,
            'stock_pct': stock_pct
        }
        
    spending_amount = round(pay_amount * (spending_pct / 100.0), 2)
    savings_amount = round(pay_amount * (savings_pct / 100.0), 2)
    total_stock_allocation = round(pay_amount - spending_amount - savings_amount, 2)

    dip_fund_allocation = round(total_stock_allocation * (dip_fund_pct_of_stock / 100.0), 2)
    active_stock_allocation = round(total_stock_allocation - dip_fund_allocation, 2)
    
    return {
        'pay_amount': round(pay_amount, 2),
        'spending_amount': spending_amount,
        'savings_amount': savings_amount,
        'stock_allocation': total_stock_allocation,
        'active_stock_allocation': active_stock_allocation,
        'dip_fund_allocation': dip_fund_allocation,
        'spending_pct': spending_pct,
        'savings_pct': savings_pct,
        'stock_pct': stock_pct
    }
