def calculate_pay_split(pay_amount, spending_pct=10.0, savings_pct=40.0, stock_pct=50.0):
    """
    Calculates the exact breakdown of an incoming pay amount:
    - 10% to Spending Account
    - 40% to Liquid Savings Account
    - 50% to Stock Investment Budget Account
    Total = 100%
    """
    if pay_amount <= 0:
        return {
            'pay_amount': 0.0,
            'spending_amount': 0.0,
            'savings_amount': 0.0,
            'stock_allocation': 0.0,
            'spending_pct': spending_pct,
            'savings_pct': savings_pct,
            'stock_pct': stock_pct
        }
        
    spending_amount = round(pay_amount * (spending_pct / 100.0), 2)
    savings_amount = round(pay_amount * (savings_pct / 100.0), 2)
    stock_allocation = round(pay_amount - spending_amount - savings_amount, 2)
    
    return {
        'pay_amount': round(pay_amount, 2),
        'spending_amount': spending_amount,
        'savings_amount': savings_amount,
        'stock_allocation': stock_allocation,
        'spending_pct': spending_pct,
        'savings_pct': savings_pct,
        'stock_pct': stock_pct
    }
