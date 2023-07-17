import yfinance as yf
import requests

def get_stock_price(ticker_symbol): 
    api_key = "a70b6167d1734f2da302664a2fb7e26a"
    url = f"https://api.twelvedata.com/price?symbol={ticker_symbol}&apikey={api_key}"
    response = requests.get(url).json()
    price = response['price'][:-3]
    return price

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