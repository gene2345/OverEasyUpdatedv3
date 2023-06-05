import yfinance as yf

def profitLoss(price, ticker):
    latest = yf.Ticker(ticker).info['regularMarketPreviousClose']
    return price - latest

def numericChecker(value):
    if value.isnumeric():
        return False
    else:
        return True
    
def totalMoney(price, qty):
    return price * qty