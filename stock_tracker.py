import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)

def fetch_aud_usd_rate():
    """
    Fetches live USD to AUD multiplier (1 USD = X AUD).
    """
    try:
        ticker = yf.Ticker("AUDUSD=X")
        aud_usd = getattr(ticker.fast_info, 'last_price', None)
        if aud_usd and aud_usd > 0:
            return round(1.0 / aud_usd, 4)
    except Exception as e:
        logging.error(f"Error fetching AUDUSD exchange rate: {e}")
    return 1.42  # Fallback exchange rate

def fetch_stock_quote(symbol):
    """
    Fetches quote for symbol via yfinance.
    """
    clean_symbol = symbol.strip().upper()
    try:
        ticker = yf.Ticker(clean_symbol)
        info = ticker.fast_info
        
        current_price = getattr(info, 'last_price', None)
        prev_close = getattr(info, 'previous_close', None)
        currency = getattr(info, 'currency', 'AUD' if clean_symbol.endswith('.AX') else 'USD')
        
        if current_price is None or current_price == 0:
            hist = ticker.history(period="2d")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price

        if current_price is None:
            return {'symbol': clean_symbol, 'valid': False, 'error': 'Price not found'}

        change = (current_price - prev_close) if prev_close else 0.0
        change_pct = (change / prev_close * 100) if (prev_close and prev_close > 0) else 0.0

        return {
            'symbol': clean_symbol,
            'current_price': round(current_price, 4),
            'previous_close': round(prev_close, 4) if prev_close else round(current_price, 4),
            'change': round(change, 4),
            'change_percent': round(change_pct, 2),
            'currency': currency or ('AUD' if clean_symbol.endswith('.AX') else 'USD'),
            'valid': True
        }
    except Exception as e:
        logging.error(f"Error fetching quote for {clean_symbol}: {e}")
        return {
            'symbol': clean_symbol,
            'valid': False,
            'current_price': 0.0,
            'change': 0.0,
            'change_percent': 0.0,
            'currency': 'AUD' if clean_symbol.endswith('.AX') else 'USD'
        }

def fetch_multiple_quotes(symbols):
    results = {}
    for sym in set(symbols):
        if sym:
            results[sym.strip().upper()] = fetch_stock_quote(sym)
    return results
