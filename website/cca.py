import yfinance as yf
from yahooquery import Ticker
import pandas as pd
import numpy as np
from datetime import datetime
import time
import traceback

#All relevant methods for API calls

#Checking its existence 
def check_existence(stock):
    skip = True
    output = Ticker(stock).price[stock]
    if "Quote not found for ticker symbol:" in output:
        print(stock, "is not found/recognised, SKIPPING")
        skip = False
    return skip

#Getting relevant data for each of the columns/ segments
def get_price_marketCap(stock):
    tick = Ticker(stock)
    ticker = tick.price[stock]
    price = ticker['regularMarketPrice']
    marketCap = ticker['marketCap']
    return price, marketCap

def get_outstandingShares_enterpriseValue_peg(stock):
    tick = Ticker(stock)
    ticker = tick.key_stats[stock]
    shares_outstanding = ticker['sharesOutstanding']
    enterprise_val = ticker['enterpriseValue']
    
    #If peg does not have a value
    try:
        peg = ticker['pegRatio']
    except:
        print('Invalid PEG Ratio for', stock)
        peg = None
        
    return shares_outstanding, enterprise_val, peg

def get_totalDebt_totalCash_EBITDA(stock):
    tick = Ticker(stock)
    ticker = tick.financial_data[stock]
    try:
        debt = ticker['totalDebt']
    except:
        debt = 0
        
    try:
        cash = ticker['totalCash']
    except:
        cash = 0
        
    try:
        ebitda = ticker['ebitda']
    except:
        ebitda = 0
        
    return debt, cash, ebitda

def get_dilutedEps_revenue(stock):
    tick = Ticker(stock)
    data = tick.all_financial_data()
    index_last = len(data) - 1
    diluted_eps = data.iloc[index_last]['DilutedEPS']
    revenue = data.iloc[index_last]['TotalRevenue']
    return diluted_eps, revenue

def get_quarterlyRevenueGrowth(stock):
    tick = Ticker(stock)
    print(stock)
    data = tick.earnings[stock]['financialsChart']['quarterly']
    total_data_num = len(data)
    starting_count = 0
    if data[len(data) - 1]['revenue'] == 0:
        starting_count = - 1
    if total_data_num >= 2:
        latest_quarter = data[len(data) - 1 + starting_count]['revenue']
        quarter_before = data[len(data) - 2 + starting_count]['revenue']
        quarterly_revenue_growth = round((latest_quarter - quarter_before) / quarter_before * 100, 2)
    else:
        quarterly_revenue_growth = 'No Data'
    return quarterly_revenue_growth

def express_in_MM(number):
    return number/1_000_000

#Can shift column headers accordingly
def column_headers():
    return ['COMPANY NAME', 'SHARE PRICE ($/share)', 'OUTSTANDING SHARES', 
                      'MARKET CAP ($M)', 'TOTAL DEBT ($M)', 'TOTAL CASH ($M)',
                     'DILUTED EPS ($/share)', 'ENTERPRISE VALUE ($)', 'REVENUE ($)',
                     'QUARTERLY REVENUE GROWTH (%)', 'EBITDA ($M)', 'EBITDA MARGIN (%)',
                     'EV/REVENUE (x)', 'EV/EBITDA (x)', 'PEG 5Y Expected (x)']
def create_df(): 
    return pd.DataFrame(columns = column_headers())

def change_to_dictionary(data_list):
    dic = {}
    #list_columns is from main >> when creating the data frame
    # Can choose to create one here or one in the main frame
    
    for i, col_name in enumerate(column_headers()):
        dic[col_name] = data_list[i]
    return dic

def check_EBITDA(stock):
    status = True
    try:
        Ticker(stock).financial_data[stock]['ebitda']
    except:
        status = False
    return status

def get_all_data(stock):
    company_name = stock
    share_price, market_cap = get_price_marketCap(stock)
    outstanding_shares, enterprise_v, peg = get_outstandingShares_enterpriseValue_peg(stock)
    total_debt, total_cash, ebitda = get_totalDebt_totalCash_EBITDA(stock)
    ev = total_debt + market_cap
    diluted_eps, revenue = get_dilutedEps_revenue(stock)
    quarterly_revenue_growth = get_quarterlyRevenueGrowth(stock)
    ebitda_margin = round(ebitda/revenue * 100, 2)
    ev_revenue = round(ev / revenue, 2)
    if ebitda == 0:
        ev_ebitda = 0
    else:
        ev_ebitda = round(ev / ebitda, 2)
    ordered_list = [company_name, share_price, outstanding_shares, round(express_in_MM(market_cap), 2),
                   round(express_in_MM(total_debt), 2), round(express_in_MM(total_cash), 2), diluted_eps, ev,
                   revenue, quarterly_revenue_growth, round(express_in_MM(ebitda), 2), 
                   ebitda_margin, ev_revenue, ev_ebitda, peg]
    return ordered_list


# For Python 3.0 and later
from urllib.request import urlopen

import certifi
import json
import urllib.request
import ssl


def get_jsonparsed_data(url):
    """
    Receive the content of ``url``, parse it as JSON and return the object.

    Parameters
    ----------
    url : str

    Returns
    -------
    dict
    """
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    response = urllib.request.urlopen(url, context=ssl_context)
    data = response.read().decode("utf-8")
    return json.loads(data)

#Identification of the current stock's industry
api_key = 'd9d5e433dd4f6a8dabb311f2c98941d0'

def scrape_peer_universe(stock):
    url = f"https://financialmodelingprep.com/api/v3/profile/{stock}?apikey={api_key}"
    industry = get_jsonparsed_data(url)[0]['industry'].split(" ")[0]
    sector = get_jsonparsed_data(url)[0]['sector'].split(" ")[0]

    #Identification of Stocks in Industry
    url_industry = f'https://financialmodelingprep.com/api/v3/stock-screener?sector={sector}&industry={industry}&limit=100&apikey={api_key}'
    exchange_lst = ['NYSE', 'NASDAQ']
    industry1 = list(filter(lambda x: x['exchangeShortName'] in exchange_lst, get_jsonparsed_data(url_industry)))

    #Can explore to include more parameters here
    #Selection of top 5 market cap firms to serve as the peer universe
    industry_sorted = sorted(industry1, key = lambda x : x['marketCap'], reverse = True)[:5]
    
    #May have to limit to NYSE and NASDAQ >> as model may not be able to look into european markets
    peer_universe = list(map(lambda x: x['symbol'], industry_sorted))
    return peer_universe


#Identifying correct peer universe
import yfinance as yf 
from yahooquery import Screener

def not_correct_industry(stock, industry):
    return not yf.Ticker(stock).info['industry'] == industry

#Peer Universe provided by YahooQuery's recommendation function
def og_peer_universe(stock, industry):
    p_universe = []
    tickers = Ticker(stock).recommendations[stock]['recommendedSymbols']
    
    for dic in tickers:
        if not_correct_industry(dic['symbol'], industry):
            continue
        p_universe.append(dic['symbol'])
    
    return p_universe


#Recommendations in the event YahooQuery's Recommendations function is not comprehensive enough
def peer_universe_(stock, industry):
    lst = og_peer_universe(stock, industry)
    if lucky_peer_universe(lst, industry) != []:
        #explore parameters to include here >> but just gonna go with the top 5
        return list(set(lucky_peer_universe(lst, industry)))[:5]
    else:
        return scrape_peer_universe(stock.upper())

#Recommendations provided by YahooQuery is applicable in the CCA valuations
def lucky_peer_universe(lst, industry):
    if lst == []:
        return []
    elif og_peer_universe(lst[0], industry) == []:
        print(type(lst))
        return [lst[0], ] + peer_universe_(lst[1:], industry)
    else:
        tickers = og_peer_universe(lst[0], industry)
        return tickers + lucky_peer_universe(lst[1:], industry)
