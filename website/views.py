from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Portfolio, PortfolioHistory
from . import db
from .calc import numericChecker, get_stock_price
from .SA import sentiment_calculator, get_fear_and_greed, finviz_scraper, yahoo_scraper, sentiment_calculator_yahoo, get_market_condition, get_market_trend, prelim_model_calc, marketaux_scraper
from .cca import get_price_marketCap, get_outstandingShares_enterpriseValue_peg, get_totalDebt_totalCash_EBITDA, get_dilutedEps_revenue, get_quarterlyRevenueGrowth, express_in_MM, get_all_data
import yfinance as yf
from .resultsCCA import *
from pretty_html_table import build_table

views = Blueprint("views", __name__)

@views.route('/', methods = ['GET', 'POST']) #homepage
@login_required
def home():
    if request.method == 'POST':
        note1 = request.form.get('note')
        note1 = note1.upper()
        try:
        #   price = yf.Ticker(note1).info['regularMarketPreviousClose']
            price = get_stock_price(note1)
            new_note = Note(data=note1, user_id = current_user.id, price = price)
            db.session.add(new_note)
            db.session.commit()
            flash("Added", category = "success")
        except:
            flash('Stock does not exist', category = "error")
    for items in Note.query:
        # items.price = yf.Ticker(items.data).info['regularMarketPreviousClose']
        items.price = get_stock_price(items.data)
        db.session.commit()
    return render_template("home.html", user = current_user)


@login_required
@views.route('/delete/<int:id>') #deleting an extra stock from homepage
def delete(id):
    note = Note.query.get(id)
    if note:
        db.session.delete(note)
        db.session.commit()
        flash("Deleted", category = "success")
    return redirect('/')

@login_required
@views.route('/CCA', methods = ['GET', 'POST'])
def cca():
    if request.method == 'POST':
        #try:
        task_content = request.form['TickerSymbol']
        df1, df2, bool1, bool2, bool3 = results(task_content)
        ticker = task_content.upper()
        return render_template("CCAresults.html", table1 = build_table(df1, 'blue_light'), table2 = build_table(df2, 'blue_light'),
                                 text = task_content, bool1 = bool1, bool2 = bool2, bool3 = bool3, user = current_user, ticker = ticker)
        #except:
            #flash("Please key in a valid stock ticker", category = "error")
            #return render_template("CCA.html", user = current_user)        
    else:
        return render_template("CCA.html", user = current_user)

@login_required #add to position in portfolio page
@views.route('/yrport', methods = ['GET', 'POST'])
def yrport():   
    if request.method == 'POST':
        stock1 = request.form.get('stock')
        stock1 = stock1.upper()
        bought_price = request.form.get('bought_price')
        bought_qty = request.form.get('bought_qty')
        if numericChecker(bought_price):
            flash("Please re enter price", category="error")
            return render_template("yrport.html", user = current_user)
        elif numericChecker(bought_qty):
            flash("Please re enter quantity", category="error")
            return render_template("yrport.html", user = current_user)
        try:
        #   price = yf.Ticker(stock1).info['regularMarketPreviousClose']
            price = get_stock_price(stock1)
            item = Portfolio.query.filter_by(data = stock1).first()
            if item is not None: #Add to history page
                old_bought_price = float(item.bought_price)
                old_bought_qty = float(item.bought_qty)
                print(old_bought_price)
                new_bought_qty = (float(bought_qty) + Portfolio.bought_qty)
                new_bought_price = (old_bought_qty*old_bought_price + float(bought_price)*float(bought_qty)) / (new_bought_qty)
                new_profitloss = (old_bought_price) - float(price)*float(old_bought_qty)
                item.bought_qty = new_bought_qty
                item.bought_price = new_bought_price
                item.profitloss = new_profitloss
                new_history = PortfolioHistory(user_id = current_user.id, status = "BUY", qty_exchanged = bought_qty, 
                                               bought_price = bought_price, sold_price = None, profitloss = None, stock = stock1)
                db.session.add(new_history)
                db.session.commit()
                flash("Detected existing stock, added to position", category = "success")
            else: #Add to history page
                profitloss = round((float(bought_price) - float(price))*float(bought_qty),2)
                new_stock = Portfolio(data=stock1, user_id = current_user.id, bought_price = bought_price, 
                                        bought_qty = bought_qty, current_price = price, profitloss = profitloss)
                new_history = PortfolioHistory(user_id = current_user.id, status = "BUY", qty_exchanged = bought_qty, 
                                               bought_price = bought_price, sold_price = None, profitloss = None, stock = stock1)
                db.session.add(new_history)
                db.session.add(new_stock)
                db.session.commit()
                flash("Added", category = "success")
        except:
            flash('Stock does not exist', category = "error")
    for items in Portfolio.query:
    #   new_price = yf.Ticker(items.data).info['regularMarketPreviousClose']
        try:
            print(type(items.data))
            print(items.data)
            new_price = get_stock_price(str(items.data))
            items.current_price = new_price
            items.profitloss = round((float(new_price) - float(items.bought_price)) * float(items.bought_qty),2)
            items.bought_price = round(items.bought_price,2)
            db.session.commit()
        except Exception as e:
            flash(e, category = "error")        
    return render_template("yrport.html", user = current_user)

@login_required
@views.route('/deleteyrport/<int:id>') #deleting an extra stock from your portfolio page
def deleteyrport(id):
    portfolio = Portfolio.query.get(id)
    if portfolio:
        db.session.delete(portfolio)
        db.session.commit()
        flash("Deleted", category = "success")
    return redirect('/yrport')

@login_required
@views.route('/stockFinder', methods = ['GET', 'POST']) #more info on a specific stock, stockfinder page
#stockfinder is essentially useless, it is about the same as more info page, can delete if no other use after milestone 1
def stockFinder():
    if request.method == 'POST':
        stock1 = request.form.get('stock').upper()
        try:
            info_list = get_all_data(stock1)
        except:
            flash('Stock does not exist', category = "error")
            info_list = []
        return render_template("stockFinder.html", user = current_user, stock_info = info_list)
    return render_template('stockFinder.html', user = current_user, stock_info = [])

@login_required
@views.route('/moreInfo/<id>') #brings you to moreInfo page
def moreInfo(id):
    info_list = get_all_data(id)
    return render_template('moreInfo.html', user = current_user, stock_info = info_list)

@login_required
@views.route('/SA', methods = ['GET', 'POST'])
def SA():
    if request.method == 'POST':
        try:
            #yahoo_sentiments = {"Positive":[0.50], "Neutral":[0.24], "Negative":[0.33]}
            ticker = request.form.get('ticker').upper()
            raw_data = yahoo_scraper(ticker)
            yahoo_sentiments = sentiment_calculator_yahoo(raw_data)
            yahoo_values = [yahoo_sentiments["Positive"][0], yahoo_sentiments["Neutral"][0], yahoo_sentiments["Negative"][0]]
            raw_data_2 = finviz_scraper(ticker)
            finviz_sentiments = sentiment_calculator(raw_data_2)
            finviz_values = [finviz_sentiments["Positive"][0], finviz_sentiments["Neutral"][0], finviz_sentiments["Negative"][0]]
            raw_data_3 = marketaux_scraper(ticker)
            aux_sentiments = sentiment_calculator(raw_data_3)
            aux_values = [aux_sentiments["Positive"][0], aux_sentiments["Neutral"][0], aux_sentiments["Negative"][0]]
            aux_trend = get_market_trend(aux_values)
            aux_sentiment = get_market_condition(aux_values)
            yahoo_trend = get_market_trend(yahoo_values)
            yahoo_sentiment = get_market_condition(yahoo_values)
            finviz_trend = get_market_trend(finviz_values)
            finviz_sentiment = get_market_condition(finviz_values)
            overall_sentiment = prelim_model_calc([finviz_values, yahoo_values, aux_values])
            labels = ["Positive", "Neutral", "Negative"]
            return render_template("SAresults.html", user = current_user, ticker = ticker, yahoo_values = yahoo_values, 
                               labels = labels, finviz_values = finviz_values, yahoo_trend = yahoo_trend,
                               yahoo_sentiment = yahoo_sentiment, finviz_trend = finviz_trend, finviz_sentiment = finviz_sentiment
                               , aux_values = aux_values, aux_sentiment = aux_sentiment, aux_trend = aux_trend, 
                               overall_sentiment = overall_sentiment)
        except Exception as e:
            flash(str(e), category = "error")
            return render_template("SA.html", user = current_user)
    else:
        return render_template("SA.html", user = current_user)

@login_required #selling a position in your portfolio
@views.route('/editPosition', methods = ['GET', 'POST'])
def editPosition():
    if request.method == 'POST':
        stock1 = request.form.get('stock')
        stock1 = stock1.upper()
        sell_price = request.form.get('sell_price')
        sell_qty = request.form.get('sell_qty')
        item = Portfolio.query.filter_by(data = stock1).first()
        if numericChecker(sell_price):
            flash("Please re enter price", category="error")
            return render_template("yrport.html", user = current_user)
        elif numericChecker(sell_qty):
            flash("Please re enter quantity", category="error")
            return render_template("yrport.html", user = current_user)
        if float(sell_qty) > item.bought_qty:
            flash("You cannot sell more than you own", category = "error")
            return render_template("yrport.html", user = current_user)
        if float(sell_qty) == item.bought_qty:
            sell_qty = float(sell_qty)
            sell_price = float(sell_price)
            profitloss = (sell_price - item.bought_price) * sell_qty
            new_history = PortfolioHistory(user_id = current_user.id, status = "SELL", qty_exchanged = sell_qty, 
                                            bought_price = None, sold_price = sell_price, profitloss = profitloss, stock = stock1)
            db.session.add(new_history)
            db.session.commit()
            db.session.delete(item)
            db.session.commit()
            flash("Successfully updated portfolio", category = "success")
            return redirect('/yrport')
        sell_qty = float(sell_qty)
        sell_price = float(sell_price)
        old_bought_qty = item.bought_qty
        new_bought_qty = old_bought_qty - sell_qty
        item.bought_qty = new_bought_qty
        profitloss = (sell_price - item.bought_price) * sell_qty
        new_history = PortfolioHistory(user_id = current_user.id, status = "SELL", qty_exchanged = sell_qty, 
                                            bought_price = None, sold_price = sell_price, profitloss = profitloss, stock = stock1)
        db.session.add(new_history)
        db.session.commit()
        flash("Successfully updated portfolio", category = "success")
    return redirect('/yrport')

@login_required
@views.route('/history')
def tester():
    return render_template("history.html", user = current_user)

@login_required
@views.route('/deletePortfolioHistory/<int:id>') #deleting an extra stock from your portfolio page
def deletePortfolioHistory(id):
    portfolioHistory = PortfolioHistory.query.get(id)
    if portfolioHistory:
        db.session.delete(portfolioHistory)
        db.session.commit()
        flash("Deleted", category = "success")
    return redirect('/history')
