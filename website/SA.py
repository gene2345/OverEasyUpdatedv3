from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from scipy.special import softmax
import pandas as pd
import numpy as np
import matplotlib.pylab as plt
import seaborn as sns
import re
import json
import csv
import requests
from transformers import AutoModelForMaskedLM
from huggingface_hub import login
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

MODEL = AutoModelForSequenceClassification.from_pretrained("KernAI/stock-news-destilbert")
tokenizer = AutoTokenizer.from_pretrained("KernAI/stock-news-destilbert")
model = AutoModelForSequenceClassification.from_pretrained("KernAI/stock-news-destilbert")

def roberta_polarity(text):
    encoded_text = tokenizer(text, return_tensors = 'pt')
    output = model(**encoded_text)
    scores = output[0][0].detach().numpy()
    scores = softmax(scores)
    return {"negative":scores[0],
           "neutral":scores[1],
           "positive":scores[2]}

def get_pos(text):
    try:
        return roberta_polarity(text)["positive"]
    except RuntimeError:
        return 0.0

def get_neut(text):
    try:
        return roberta_polarity(text)["neutral"]
    except RuntimeError:
        return 0.0

def get_neg(text):
    try:
        return roberta_polarity(text)["negative"]
    except RuntimeError:
        return 0.0
    
def sentiment_calculator(lister): #input a list of texts and returns dictionary
    positive = 0.0
    negative = 0.0
    neutral = 0.0

    for text in lister:
        positive += get_pos(text)
        negative += get_neg(text)
        neutral += get_neut(text)
      
    positive = positive / len(lister)
    negative = negative / len(lister)
    neutral = neutral / len(lister)

    d = {
    "Positive" : [positive,],
    "Neutral" : [neutral,],
    "Negative" : [negative,]
    }

    return d

def sentiment_calculator_yahoo(lister):
    positive = 0.0
    negative = 0.0
    neutral = 0.0

    length = len(lister["conversation"]['comments'])
    for i in range(length):
        if i == 0:
            continue
        try:
            text = lister["conversation"]['comments'][i]['content'][0]['text']
            positive += get_pos(text)
            negative += get_neg(text)
            neutral += get_neut(text)
        except KeyError:
            continue
      
    positive = positive / length
    negative = negative / length
    neutral = neutral / length

    d = {
    "Positive" : [positive,],
    "Neutral" : [neutral,],
    "Negative" : [negative,]
    }

    return d



def finviz_scraper(ticker):
    finviz_url = 'http://finviz.com/quote.ashx?t='

    news_tables = {}
    url = finviz_url + ticker
    req = Request(url=url, headers = {'user-agent': 'my-app'})
    response = urlopen(req)

    html = BeautifulSoup(response, 'html.parser')
    news_table = html.find(id = 'news-table')
    news_tables[ticker] = news_table

    parsed_data = []

    for ticker, news_table in news_tables.items():
    
        for row in news_table.findAll('tr'):
        
            title = row.a.get_text()
            date_data = row.td.text.split(" ")
        
            if len(date_data) == 1:
                time = date_data[0]
            else:
                time = date_data[0]
                date = date_data[1]
            
            parsed_data.append([ticker, date, time, title])

    texts = []
    for rows in parsed_data:
        texts.append(rows[-1])
    
    return texts

def marketaux_scraper(ticker): 
    api_key = "zFqAcB0Hh17YwvQ4FcnkOq5egzEVnGJuWBvW1Rey"
    url = f"https://api.marketaux.com/v1/news/all?symbols={ticker}&filter_entities=true&language=en&api_token={api_key}"
    response = requests.get(url).json()
    
    text_list = []
    
    for inputs in response['data']:
        text_list.append(inputs['title'])
        text_list.append(inputs['description'])
        text_list.append(inputs['snippet'])
        text_list.append(inputs['entities'][0]['highlights'][0]['highlight'])  
    
    return text_list


def yahoo_scraper(ticker):
    url = f'https://finance.yahoo.com/quote/{ticker}/community'
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'})
    soup = BeautifulSoup(response.text, 'html.parser')
    data = json.loads(soup.select_one('#spotim-config').get_text(strip=True))['config']

    url = "https://api-2-0.spot.im/v1.0.0/conversation/read"
    payload = json.dumps({
    "conversation_id": data['spotId'] + data['uuid'].replace('_', '$'),
    "count": 250,
    "offset": 0
    })
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
    'Content-Type': 'application/json',
    'x-spot-id': data['spotId'],
    'x-post-id': data['uuid'].replace('_', '$'),
    }

    response = requests.post(url, headers=headers, data=payload)
    data = response.json()

    return data

def get_fear_and_greed():

    options = Options()
    options.add_argument("--headless=new")

    driver = webdriver.Chrome(options = options)
    driver.get('https://en.macromicro.me/charts/50108/cnn-fear-and-greed')
    
    # search = driver.find_element_by_name("s")
    # search.send_keys("test")
    # search.send_keys(Keys.RETURN)

    classer = driver.find_element(By.XPATH, "/html/body/div[1]/div/main/div/div[2]/div[1]/div/div/div[2]/div[4]/ul/li[1]/div[3]/span[1]")
    driver.quit()

    return classer.text

def get_market_trend(lister):
    if lister[0] > lister[2]:
        return "Bullish"
    elif lister[0] == lister[2]:
        return "Neutral"
    else:
        return "Bearish"

def get_market_condition(lister):
    if lister[0] > lister[2]:
        return "Positive"
    elif lister[0] == lister[2]:
        return "Neutral"
    else:
        return "Negative"
    
def prelim_model_calc(list_of_sentiments):
    pos_count = 0
    neg_count = 0
    for listers in list_of_sentiments:
        pos_count += listers[0]
        neg_count += listers[2]
    if pos_count > neg_count:
        return "Bullish"
    elif neg_count > pos_count:
        return "Bearish"
    else:
        return "Neutral"