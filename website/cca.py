import pandas as pd
import numpy as np
from datetime import datetime

from urllib.request import urlopen
import certifi
import json
import urllib.request
import ssl
import requests

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
    response = urllib.request.urlopen(url).read().decode("utf-8", errors = 'ignore')
    #data = response.read().decode("utf-8")
    return json.loads(response)
#api_key = 'ad5a88392bb3f5a0db84d4f8a9311d75'
api_key = '7ea6336e5a6e7041b10e17edb74f3269'
#api_key = "9b54dd736d3502fa23f9343e0994244b"

#All relevant methods for API calls

#Checking its existence (see whether can try to beautify)
def check_existence(stock):
    url = f"https://financialmodelingprep.com/api/v3/profile/{stock}?apikey={api_key}"
    skip = True
    if not get_jsonparsed_data(url):
        print(stock, "is not found/recognised, SKIPPING")
        skip = False
    return skip

#Getting relevant data for each of the columns/ segments >> enterprise values
def get_marketCap_outstandingShares_enterpriseValue_debt_cash(stock):
    url = f"https://financialmodelingprep.com/api/v3/enterprise-values/{stock}?limit=40&apikey={api_key}"
    data = get_jsonparsed_data(url)[0]
    return data["marketCapitalization"], data["numberOfShares"], data["enterpriseValue"], data["addTotalDebt"], data["minusCashAndCashEquivalents"]

def get_price(stock):
    url = f"https://financialmodelingprep.com/api/v3/profile/{stock}?limit=40&apikey={api_key}"
    data = get_jsonparsed_data(url)[0]
    return data["price"]

#Get from International Filings
def get_revenue_ebitda_eps(stock):
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{stock}?limit=10&apikey={api_key}"
    data = get_jsonparsed_data(url)[0]
    return data['revenue'], data['ebitda'], data['eps']

#Get from Company Financial Ratios
def get_peg(stock):
    url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{stock}?apikey={api_key}"
    data = get_jsonparsed_data(url)[0]
    return data['pegRatioTTM']

# Get from Financial Statements Growth
def get_revenueGrowth_ebidtaGrowth(stock):
    url = f"https://financialmodelingprep.com/api/v3/income-statement-growth/{stock}?apikey={api_key}&limit=40"
    data = get_jsonparsed_data(url)[0]
    return data["growthRevenue"], data["growthEBITDA"]

def express_in_MM(number):
    return number/1_000_000

#Can shift column headers accordingly
def column_headers():
    return ['COMPANY NAME', 'SHARE PRICE ($/share)', 'OUTSTANDING SHARES', 
                      'MARKET CAP ($M)', 'TOTAL DEBT ($M)', 'TOTAL CASH ($M)',
                     'DILUTED EPS ($/share)', 'ENTERPRISE VALUE ($)', 'REVENUE ($)',
                     'REVENUE GROWTH (%)', 'EBITDA GROWTH (%)', 'EBITDA ($M)', 'EBITDA MARGIN (%)',
                     'EV/REVENUE (x)', 'EV/EBITDA (x)', 'PEG ratio TTM (x)']
def create_df(): 
    return pd.DataFrame(columns = column_headers())

def change_to_dictionary(data_list):
    dic = {}
    #list_columns is from main >> when creating the data frame
    # Can choose to create one here or one in the main frame
    
    for i, col_name in enumerate(column_headers()):
        dic[col_name] = data_list[i]
    return dic

# def check_EBITDA(stock):
    # status = True
    # try:
    #     Ticker(stock).financial_data[stock]['ebitda']
    # except:
    #     status = False
    # return status

def get_all_data(stock):
    company_name = stock
    market_cap, outstanding_shares, enterprise_v, total_debt, total_cash = get_marketCap_outstandingShares_enterpriseValue_debt_cash(stock)
    share_price = get_price(stock)
    peg = get_peg(stock)
    ev = total_debt + market_cap
    revenue, ebitda, diluted_eps = get_revenue_ebitda_eps(stock)
    revenue_growth, ebitda_growth = get_revenueGrowth_ebidtaGrowth(stock)
    ebitda_margin = round(ebitda/revenue * 100, 2)
    ev_revenue = round(ev / revenue, 2)
    if ebitda == 0:
        ev_ebitda = 0
    else:
        ev_ebitda = round(ev / ebitda, 2)
    ordered_list = [company_name, share_price, outstanding_shares, round(express_in_MM(market_cap), 2),
                   round(express_in_MM(total_debt), 2), round(express_in_MM(total_cash), 2), diluted_eps, enterprise_v,
                   revenue, revenue_growth, ebitda_growth, round(express_in_MM(ebitda), 2), 
                   ebitda_margin, ev_revenue, ev_ebitda, round(peg, 2)]
    return ordered_list

#print(get_all_data('aapl'))

#Identifying correct peer universe
def not_correct_industry(stock, industry):
    url = f"https://financialmodelingprep.com/api/v3/profile/{stock}?apikey={api_key}"
    return get_jsonparsed_data(url)[0]['industry'] == industry

#print(not_correct_industry('aapl', 'Consumer Electronics'))

#Identification of the current stock's industry
def peer_universe(stock):
    url = f"https://financialmodelingprep.com/api/v3/profile/{stock}?apikey={api_key}"
    #industry = get_jsonparsed_data(url)[0]['industry'].split(" ")[0]
    sector = get_jsonparsed_data(url)[0]['sector'].split(" ")[0]
    market_cap = get_jsonparsed_data(url)[0]["mktCap"]

    #Identification of Stocks in Industry
    url_industry = f'https://financialmodelingprep.com/api/v3/stock-screener?sector={sector}&limit=100&apikey={api_key}'
    exchange_lst = ['NYSE', 'NASDAQ']
    industry1 = list(filter(lambda x: x['exchangeShortName'] in exchange_lst, get_jsonparsed_data(url_industry)))
    #Can explore to include more parameters here
    #Selection of top 5 most similar market cap firms to serve as the peer universe
    industry_sorted = sorted(industry1, key = lambda x : (x['marketCap'] - market_cap) ** 2)[:5]
    
    #May have to limit to NYSE and NASDAQ >> as model may not be able to look into european markets
    p_universe = list(map(lambda x: x['symbol'], industry_sorted))
    return p_universe

##### YFINANCE METHODS #####
#I need PEG >> Calculate with Ratios, skip first
# def get_outstandingShares_enterpriseValue_peg(stock):
#     tick = Ticker(stock)
#     ticker = tick.key_stats[stock]
#     shares_outstanding = ticker['sharesOutstanding']
#     enterprise_val = ticker['enterpriseValue']
    
#     #If peg does not have a value
#     try:
#         peg = ticker['pegRatio']
#     except:
#         print('Invalid PEG Ratio for', stock)
#         peg = None
        
#     return shares_outstanding, enterprise_val, peg

#Testing get_outstandingShares_enterpriseValue_peg
#print(get_outstandingShares_enterpriseValue_peg('aapl'))

# def get_totalDebt_totalCash_EBITDA(stock):
#     tick = Ticker(stock)
#     ticker = tick.financial_data[stock]
#     try:
#         debt = ticker['totalDebt']
#     except:
#         debt = 0
        
#     try:
#         cash = ticker['totalCash']
#     except:
#         cash = 0
        
#     try:
#         ebitda = ticker['ebitda']
#     except:
#         ebitda = 0
        
#     return debt, cash, ebitda

#Testing get_totalDebt_totalCash_EBITDA
#print(get_totalDebt_totalCash_EBITDA('aapl'))

# def get_dilutedEps_revenue(stock):
#     tick = Ticker(stock)
#     data = tick.all_financial_data()
#     index_last = len(data) - 1
#     diluted_eps = data.iloc[index_last]['DilutedEPS']
#     revenue = data.iloc[index_last]['TotalRevenue']
#     return diluted_eps, revenue

#Testing get_dilutedEps_revenue
#print(get_dilutedEps_revenue('aapl'))

# def get_quarterlyRevenueGrowth(stock):
#     tick = Ticker(stock)
#     print(stock)
#     data = tick.earnings[stock]['financialsChart']['quarterly']
#     total_data_num = len(data)
#     starting_count = 0
#     if data[len(data) - 1]['revenue'] == 0:
#         starting_count = - 1
#     if total_data_num >= 2:
#         latest_quarter = data[len(data) - 1 + starting_count]['revenue']
#         quarter_before = data[len(data) - 2 + starting_count]['revenue']
#         quarterly_revenue_growth = round((latest_quarter - quarter_before) / quarter_before * 100, 2)
#     else:
#         quarterly_revenue_growth = 'No Data'
#     return quarterly_revenue_growth
###### YFINANCE METHODS END ######

##### YFINANCE METHODS #####
# #Identifying correct peer universe
# def not_correct_industry(stock, industry):
#     return not yf.Ticker(stock).info['industry'] == industry

#Peer Universe provided by YahooQuery's recommendation function
# def og_peer_universe(stock, industry):
#     p_universe = []
#     tickers = Ticker(stock).recommendations[stock]['recommendedSymbols']
    
#     for dic in tickers: 
#         if not_correct_industry(dic['symbol'], industry):
#             continue
#         p_universe.append(dic['symbol'])
    
#     return p_universe

#Recommendations provided by YahooQuery is applicable in the CCA valuations
# def lucky_peer_universe(lst, industry):
#     if lst == []:
#         return []
#     elif og_peer_universe(lst[0], industry) == []:
#         print(type(lst))
#         return [lst[0], ] + lucky_peer_universe(lst[1:], industry)
#     else:
#         tickers = og_peer_universe(lst[0], industry)
#         return tickers + lucky_peer_universe(lst[1:], industry)

#Recommendations in the event YahooQuery's Recommendations function is not comprehensive enough
# def peer_universe_(stock, industry):
#     lst = og_peer_universe(stock, industry)
#     if lucky_peer_universe(lst, industry) != []:
#         #explore parameters to include here >> but just gonna go with the top 5
#         return list(set(lucky_peer_universe(lst, industry)))[:5]
#     else:
#         return scrape_peer_universe(stock.upper())

#Recommendations in the event YahooQuery's Recommendations function is not comprehensive enough
# def peer_universe_(stock, industry):
#     lst = og_peer_universe(stock, industry)
#     if lucky_peer_universe(lst, industry) != []:
#         #explore parameters to include here >> but just gonna go with the top 5
#         return list(set(lucky_peer_universe(lst, industry)))[:5]
#     else:
#         return scrape_peer_universe(stock.upper())

##### YFINANCE END #####

