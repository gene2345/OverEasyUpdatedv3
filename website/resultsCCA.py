import yfinance as yf
from yahooquery import Ticker
import pandas as pd
import numpy as np
from datetime import datetime
import time
from .cca import *

#Main >> To execute main code


#Generation of Peer Universe

def results(tickerS):
    df = create_df()

    stock = tickerS.lower()
    try:
        stock_industry = yf.Ticker(stock).info['industry']
    except:
        return "Incorrect Stock Ticker"

    #Check Validity of Ticker
    if check_existence(stock):
        # develop peer universe via the yahooquery API
        peer_universe = peer_universe_(stock, stock_industry)
        print(peer_universe)
        if stock.upper() in peer_universe:
            peer_universe.remove(stock.upper())
        peer_universe.append(stock.upper())

        #Loop through peer universe list + create dataframe
        for ticker in peer_universe:
            print("Getting data for: ", ticker)
            if not check_EBITDA(ticker):
                continue
            ticker_data_dict = change_to_dictionary(get_all_data(ticker))
            df_result_temp = pd.DataFrame(ticker_data_dict, index = [0])
            df = pd.concat([df, df_result_temp], ignore_index = True)
        
        #Calculating Industry Average
        print("Calculating Industry Averages")
        columns_in_question = ['EBITDA MARGIN (%)','EV/REVENUE (x)',
                            'EV/EBITDA (x)','PEG 5Y Expected (x)']
        
        industry_row_dict = {}
        for col in columns_in_question:
            if col == 'COMPANY NAME':
                industry_row_dict[col] = 'Average'
            elif col in columns_in_question:
                industry_row_dict[col] = df[col].mean()
            else:
                industry_row_dict[col] = None
        
        df_avg = pd.DataFrame(industry_row_dict, index = [0])
        df = pd.concat([df, df_avg], ignore_index = True)
        
        #Asssessing Intrinsic Value of company
        intrinsic_ratio = df.iloc[len(df) - 1 ]['EV/EBITDA (x)']
        print(intrinsic_ratio)
        df['Relative Fair Value'] = ((intrinsic_ratio * df['EBITDA ($M)'] * 1_000_000) - (df['TOTAL DEBT ($M)'] * 1_000_000)) / df['OUTSTANDING SHARES']
        
        #Include a column that suggests whether they are undervalued or overvalued
        
        #Completion of dataframes
        print("Results preview")
        industry_values = df.iloc[-1]
        
        ticker_values = df.iloc[-2]
        return df, industry_values['EBITDA MARGIN (%)'] < ticker_values['EBITDA MARGIN (%)'], industry_values['EV/REVENUE (x)'] > ticker_values['EV/REVENUE (x)'], ticker_values['ENTERPRISE VALUE ($)'] < industry_values['EV/EBITDA (x)'] * ticker_values['EBITDA ($M)'] * 1000000
        
    else:
        return "Incorrect Stock Ticker"
