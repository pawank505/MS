
#**************** IMPORT PACKAGES ********************
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify

import requests
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import math, random
from datetime import datetime
import datetime as dt
import yfinance as yf
import tweepy
import preprocessor as p
import re
from sklearn.linear_model import LinearRegression
from textblob import TextBlob
import constants as ct
from Tweet import Tweet
import nltk
nltk.download('punkt')

# Ignore Warnings
import warnings
warnings.filterwarnings("ignore")
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

#***************** FLASK *****************************
app = Flask(__name__)

#To control caching so as to save and retrieve plot figs on client side
# @app.after_request
# def add_header(response):
#     response.headers['Pragma'] = 'no-cache'
#     response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
#     response.headers['Expires'] = '0'
#     return response
# @app.route('/get_static_tweets')
# def get_static_tweets():
#         tweets = [
#             {"full_text": "$AAPL Wen Apple iRobot? 🚀 🌕", "polarity": 0.5},  # Sentiment: Bullish
#             {"full_text": "$AAPL $TSLA $GOEV absolutely nonsense, Tesla got the ability to design and build the van. Why would he spend money to buy a company with many debts? Or r Tesla may buy the design patent after canoo go bankrupt", "polarity": -0.2},  # Sentiment: Negative
#             {"full_text": "$NKE $TSLA $AAPL $GOOGL $GOOG", "polarity": 0.1}  # Sentiment: Neutral (visible for GOOGL)
#         ]


#         tw_list = []
#         global_polarity = 0
#         pos, neg = 0, 0

#         for tweet in tweets:
#             full_text = tweet['full_text']
#             polarity = tweet['polarity']

#             if polarity > 0:
#                 pos += 1
#             elif polarity < 0:
#                 neg += 1
#             global_polarity += polarity

#             tw_list.append({"text": full_text, "polarity": polarity})

#         neutral = len(tweets) - pos - neg
#         if len(tw_list) != 0:
#             global_polarity /= len(tw_list)

#         tw_pol = "Overall Positive" if global_polarity > 0 else "Overall Negative"
#         for tw in tw_list:
#             print(tw)
#         return jsonify({
#             "tweet_list": [tweet['text'] for tweet in tw_list],
#             "polarity": tw_pol,
#             "positive": pos,
#             "negative": neg,
#             "neutral": neutral
#         })
@app.route('/get_static_tweets')
def get_static_tweets():
    # Static list of tweets
    tweets = [
        {"full_text": "$AAPL Wen Apple iRobot? 🚀 🌕", "polarity": 0.5},  # Sentiment: Bullish
        {"full_text": "$AAPL $TSLA $GOEV absolutely nonsense, Tesla got the ability to design and build the van. Why would he spend money to buy a company with many debts? Or r Tesla may buy the design patent after canoo go bankrupt", "polarity": -0.2},  # Sentiment: Negative
        {"full_text": "$NKE $TSLA $AAPL $GOOGL $GOOG", "polarity": 0.1}  # Sentiment: Neutral (visible for GOOGL)
    ]

    # Get the symbol parameter from the request (e.g., ?symbol=AAPL)
    symbol = request.args.get('symbol', default=None)

    # Filter tweets based on the symbol (if provided)
    if symbol:
        tweets = [tweet for tweet in tweets if f"${symbol.upper()}" in tweet['full_text']]

    tw_list = []
    global_polarity = 0
    pos, neg = 0, 0

    for tweet in tweets:
        full_text = tweet['full_text']
        polarity = tweet['polarity']

        # Update sentiment counts
        if polarity > 0:
            pos += 1
        elif polarity < 0:
            neg += 1
        global_polarity += polarity

        # Append the tweet to the list
        tw_list.append({"text": full_text, "polarity": polarity})

    # Calculate the neutral count
    neutral = len(tweets) - pos - neg

    # If there are tweets, calculate global polarity
    if len(tw_list) != 0:
        global_polarity /= len(tw_list)

    # Determine the overall polarity
    tw_pol = "Overall Positive" if global_polarity > 0 else "Overall Negative"

    # Print out each tweet (optional, for debugging purposes)
    for tw in tw_list:
        print(tw)

    # Return the response in JSON format
    return jsonify({
        "tweet_list": [tweet['text'] for tweet in tw_list],
        "polarity": tw_pol,
        "positive": pos,
        "negative": neg,
        "neutral": neutral
    })

@app.route('/')
def index():
   return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template()
@app.route('/sentiment_data')
def sentiment_data():
    # Example API data (replace with actual API call)
    api_data = {
        "messages": [
            {"body": "$AAPL He’s a winner."},
            {"body": "$MSFT He’s a loser."},
            {"body": "$AAPL Bullish sentiment!"},
            {"body": "$SPY Neutral day"}
        ]
    }

    # Initialize VADER sentiment analyzer
    analyzer = SentimentIntensityAnalyzer()

    # Initialize sentiment counts
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

    # Analyze each message's sentiment
    for message in api_data["messages"]:
        sentiment = analyzer.polarity_scores(message["body"])

        if sentiment["compound"] >= 0.05:
            sentiment_counts["positive"] += 1
        elif sentiment["compound"] <= -0.05:
            sentiment_counts["negative"] += 1
        else:
            sentiment_counts["neutral"] += 1

    # Return the data in JSON format
    return jsonify(sentiment_counts)
@app.route('/insertintotable',methods = ['POST'])
def insertintotable():
    nm = request.form['nm']

    #**************** FUNCTIONS TO FETCH DATA ***************************
    def get_historical(quote):
        end = datetime.now()
        start = datetime(end.year-2,end.month,end.day)
        data = yf.download(quote, start=start, end=end)
        df = pd.DataFrame(data=data)
        df.to_csv(''+quote+'.csv')
        if(df.empty):
            ts = TimeSeries(key='N6A6QT6IBFJOPJ70',output_format='pandas')
            data, meta_data = ts.get_daily_adjusted(symbol='NSE:'+quote, outputsize='full')
            #Format df
            #Last 2 yrs rows => 502, in ascending order => ::-1
            data=data.head(503).iloc[::-1]
            data=data.reset_index()
            #Keep Required cols only
            df=pd.DataFrame()
            df['Date']=data['date']
            df['Open']=data['1. open']
            df['High']=data['2. high']
            df['Low']=data['3. low']
            df['Close']=data['4. close']
            df['Adj Close']=data['5. adjusted close']
            df['Volume']=data['6. volume']
            df.to_csv(''+quote+'.csv',index=False)
        return df

    #******************** ARIMA SECTION ********************
    def ARIMA_ALGO(df):
        uniqueVals = df["Code"].unique()  
        len(uniqueVals)
        df=df.set_index("Code")
        #for daily basis
        def parser(x):
            return datetime.strptime(x, '%Y-%m-%d')
        def arima_model(train, test):
            history = [x for x in train]
            predictions = list()
            for t in range(len(test)):
                model = ARIMA(history, order=(6,1 ,0))
                model_fit = model.fit()
                output = model_fit.forecast()
                yhat = output[0]
                predictions.append(yhat)
                obs = test[t]
                history.append(obs)
            return predictions
        for company in uniqueVals[:10]:
            data=(df.loc[company,:]).reset_index()
            data['Price'] = data['Close']
            Quantity_date = data[['Price','Date']]
            Quantity_date.index = Quantity_date['Date'].map(lambda x: parser(x))
            Quantity_date['Price'] = Quantity_date['Price'].map(lambda x: float(x))
            Quantity_date = Quantity_date.fillna(Quantity_date.bfill())
            Quantity_date = Quantity_date.drop(['Date'],axis =1)
            fig = plt.figure(figsize=(7.2,4.8),dpi=65)
            plt.plot(Quantity_date)
            plt.savefig('static/Trends.png')
            plt.close(fig)
            
            quantity = Quantity_date.values
            size = int(len(quantity) * 0.80)
            train, test = quantity[0:size], quantity[size:len(quantity)]
            #fit in model
            predictions = arima_model(train, test)
            
            #plot graph
            fig = plt.figure(figsize=(7.2,4.8),dpi=65)
            plt.plot(test,label='Actual Price')
            plt.plot(predictions,label='Predicted Price')
            plt.legend(loc=4)
            plt.savefig('static/ARIMA.png')
            plt.close(fig)
            print()
            print("##############################################################################")
            arima_pred=predictions[-2]
            print("Tomorrow's",quote," Closing Price Prediction by ARIMA:",arima_pred)
            #rmse calculation
            error_arima = math.sqrt(mean_squared_error(test, predictions))
            print("ARIMA RMSE:",error_arima)
            print("##############################################################################")
            return arima_pred, error_arima
        
        


    #************* LSTM SECTION **********************

    def LSTM_ALGO(df):
        #Split data into training set and test set
        dataset_train=df.iloc[0:int(0.8*len(df)),:]
        dataset_test=df.iloc[int(0.8*len(df)):,:]
        ############# NOTE #################
        #TO PREDICT STOCK PRICES OF NEXT N DAYS, STORE PREVIOUS N DAYS IN MEMORY WHILE TRAINING
        # HERE N=7
        ###dataset_train=pd.read_csv('Google_Stock_Price_Train.csv')
        training_set=df.iloc[:,4:5].values# 1:2, to store as numpy array else Series obj will be stored
        #select cols using above manner to select as float64 type, view in var explorer

        #Feature Scaling
        from sklearn.preprocessing import MinMaxScaler
        sc=MinMaxScaler(feature_range=(0,1))#Scaled values btween 0,1
        training_set_scaled=sc.fit_transform(training_set)
        #In scaling, fit_transform for training, transform for test
        
        #Creating data stucture with 7 timesteps and 1 output. 
        #7 timesteps meaning storing trends from 7 days before current day to predict 1 next output
        X_train=[]#memory with 7 days from day i
        y_train=[]#day i
        for i in range(7,len(training_set_scaled)):
            X_train.append(training_set_scaled[i-7:i,0])
            y_train.append(training_set_scaled[i,0])
        #Convert list to numpy arrays
        X_train=np.array(X_train)
        y_train=np.array(y_train)
        X_forecast=np.array(X_train[-1,1:])
        X_forecast=np.append(X_forecast,y_train[-1])
        #Reshaping: Adding 3rd dimension
        X_train=np.reshape(X_train, (X_train.shape[0],X_train.shape[1],1))#.shape 0=row,1=col
        X_forecast=np.reshape(X_forecast, (1,X_forecast.shape[0],1))
        #For X_train=np.reshape(no. of rows/samples, timesteps, no. of cols/features)
        
        #Building RNN
        from keras.models import Sequential # type: ignore
        from keras.layers import Dense # type: ignore
        from keras.layers import Dropout # type: ignore
        from keras.layers import LSTM # type: ignore
        
        #Initialise RNN
        regressor=Sequential()
        
        #Add first LSTM layer
        regressor.add(LSTM(units=50,return_sequences=True,input_shape=(X_train.shape[1],1)))
        #units=no. of neurons in layer
        #input_shape=(timesteps,no. of cols/features)
        #return_seq=True for sending recc memory. For last layer, retrun_seq=False since end of the line
        regressor.add(Dropout(0.1))
        
        #Add 2nd LSTM layer
        regressor.add(LSTM(units=50,return_sequences=True))
        regressor.add(Dropout(0.1))
        
        #Add 3rd LSTM layer
        regressor.add(LSTM(units=50,return_sequences=True))
        regressor.add(Dropout(0.1))
        
        #Add 4th LSTM layer
        regressor.add(LSTM(units=50))
        regressor.add(Dropout(0.1))
        
        #Add o/p layer
        regressor.add(Dense(units=1))
        
        #Compile
        regressor.compile(optimizer='adam',loss='mean_squared_error')
        
        #Training
        regressor.fit(X_train,y_train,epochs=25,batch_size=32 )
        #For lstm, batch_size=power of 2
        
        #Testing
        ###dataset_test=pd.read_csv('Google_Stock_Price_Test.csv')
        real_stock_price=dataset_test.iloc[:,4:5].values
        
        #To predict, we need stock prices of 7 days before the test set
        #So combine train and test set to get the entire data set
        dataset_total=pd.concat((dataset_train['Close'],dataset_test['Close']),axis=0) 
        testing_set=dataset_total[ len(dataset_total) -len(dataset_test) -7: ].values
        testing_set=testing_set.reshape(-1,1)
        #-1=till last row, (-1,1)=>(80,1). otherwise only (80,0)
        
        #Feature scaling
        testing_set=sc.transform(testing_set)
        
        #Create data structure
        X_test=[]
        for i in range(7,len(testing_set)):
            X_test.append(testing_set[i-7:i,0])
            #Convert list to numpy arrays
        X_test=np.array(X_test)
        
        #Reshaping: Adding 3rd dimension
        X_test=np.reshape(X_test, (X_test.shape[0],X_test.shape[1],1))
        
        #Testing Prediction
        predicted_stock_price=regressor.predict(X_test)
        
        #Getting original prices back from scaled values
        predicted_stock_price=sc.inverse_transform(predicted_stock_price)
        fig = plt.figure(figsize=(7.2,4.8),dpi=65)
        plt.plot(real_stock_price,label='Actual Price')  
        plt.plot(predicted_stock_price,label='Predicted Price')
          
        plt.legend(loc=4)
        plt.savefig('static/LSTM.png')
        plt.close(fig)
        
        
        error_lstm = math.sqrt(mean_squared_error(real_stock_price, predicted_stock_price))
        
        
        #Forecasting Prediction
        forecasted_stock_price=regressor.predict(X_forecast)
        
        #Getting original prices back from scaled values
        forecasted_stock_price=sc.inverse_transform(forecasted_stock_price)
        
        lstm_pred=forecasted_stock_price[0,0]
        print()
        print("##############################################################################")
        print("Tomorrow's ",quote," Closing Price Prediction by LSTM: ",lstm_pred)
        print("LSTM RMSE:",error_lstm)
        print("##############################################################################")
        return lstm_pred,error_lstm
    #***************** LINEAR REGRESSION SECTION ******************       
    def LIN_REG_ALGO(df):
        #No of days to be forcasted in future
        forecast_out = int(7)
        #Price after n days
        df['Close after n days'] = df['Close'].shift(-forecast_out)
        #New df with only relevant data
        df_new=df[['Close','Close after n days']]

        #Structure data for train, test & forecast
        #lables of known data, discard last 35 rows
        y =np.array(df_new.iloc[:-forecast_out,-1])
        y=np.reshape(y, (-1,1))
        #all cols of known data except lables, discard last 35 rows
        X=np.array(df_new.iloc[:-forecast_out,0:-1])
        #Unknown, X to be forecasted
        X_to_be_forecasted=np.array(df_new.iloc[-forecast_out:,0:-1])
        
        #Traning, testing to plot graphs, check accuracy
        X_train=X[0:int(0.8*len(df)),:]
        X_test=X[int(0.8*len(df)):,:]
        y_train=y[0:int(0.8*len(df)),:]
        y_test=y[int(0.8*len(df)):,:]
        
        # Feature Scaling===Normalization
        from sklearn.preprocessing import StandardScaler
        sc = StandardScaler()
        X_train = sc.fit_transform(X_train)
        X_test = sc.transform(X_test)
        
        X_to_be_forecasted=sc.transform(X_to_be_forecasted)
        
        #Training
        clf = LinearRegression(n_jobs=-1)
        clf.fit(X_train, y_train)
        
        #Testing
        y_test_pred=clf.predict(X_test)
        y_test_pred=y_test_pred*(1.04)
        import matplotlib.pyplot as plt2
        fig = plt2.figure(figsize=(7.2,4.8),dpi=65)
        plt2.plot(y_test,label='Actual Price' )
        plt2.plot(y_test_pred,label='Predicted Price')
        
        plt2.legend(loc=4)
        plt2.savefig('static/LR.png')
        plt2.close(fig)
        
        error_lr = math.sqrt(mean_squared_error(y_test, y_test_pred))
        
        
        #Forecasting
        forecast_set = clf.predict(X_to_be_forecasted)
        forecast_set=forecast_set*(1.04)
        mean=forecast_set.mean()
        lr_pred=forecast_set[0,0]
        print()
        print("##############################################################################")
        print("Tomorrow's ",quote," Closing Price Prediction by Linear Regression: ",lr_pred)
        print("Linear Regression RMSE:",error_lr)
        print("##############################################################################")
        return df, lr_pred, forecast_set, mean, error_lr
    #**************** SENTIMENT ANALYSIS **************************

    
    # @app.route('/get_static_tweets')
    # def get_static_tweets():
    #     tweets = [
    #         {"full_text": "Tesla stock price soars after announcement.", "polarity": 0.5},
    #         {"full_text": "Tesla faces challenges with new production line.", "polarity": -0.3},
    #         {"full_text": "Investors optimistic about Tesla's future.", "polarity": 0.7}
    #     ]

    #     tw_list = []
    #     global_polarity = 0
    #     pos, neg = 0, 0

    #     for tweet in tweets:
    #         full_text = tweet['full_text']
    #         polarity = tweet['polarity']

    #         if polarity > 0:
    #             pos += 1
    #         elif polarity < 0:
    #             neg += 1
    #         global_polarity += polarity

    #         tw_list.append({"text": full_text, "polarity": polarity})

    #     neutral = len(tweets) - pos - neg
    #     if len(tw_list) != 0:
    #         global_polarity /= len(tw_list)

    #     tw_pol = "Overall Positive" if global_polarity > 0 else "Overall Negative"

    #     return jsonify({
    #         "tweet_list": [tweet['text'] for tweet in tw_list],
    #         "polarity": tw_pol,
    #         "positive": pos,
    #         "negative": neg,
    #         "neutral": neutral
    #     })
    # @app.route('/result')
    # def result():
    #         tweet_data = get_static_tweets()  # Call your function
    #         return render_template('result.html', tweets=tweet_data['tweet_list'])

    def recommending(df, global_polarity,today_stock,mean):
        if today_stock.iloc[-1]['Close'] < mean:
            if global_polarity > 0:
                idea="RISE"
                decision="BUY"
                print()
                print("##############################################################################")
                print("According to the ML Predictions and Sentiment Analysis of Tweets, a",idea,"in",quote,"stock is expected => ",decision)
            elif global_polarity <= 0:
                idea="FALL"
                decision="SELL"
                print()
                print("##############################################################################")
                print("According to the ML Predictions and Sentiment Analysis of Tweets, a",idea,"in",quote,"stock is expected => ",decision)
        else:
            idea="FALL"
            decision="SELL"
            print()
            print("##############################################################################")
            print("According to the ML Predictions and Sentiment Analysis of Tweets, a",idea,"in",quote,"stock is expected => ",decision)
        return idea, decision





    #**************GET DATA ***************************************
    quote=nm
    #Try-except to check if valid stock symbol
    try:
        get_historical(quote)
        # get_tweets(quote)
        get_static_tweets()
       
    except:
        return render_template('index.html',not_found=True)
    else:
    
        #************** PREPROCESSUNG ***********************
        df = pd.read_csv(''+quote+'.csv')
        print("##############################################################################")
        print("Today's",quote,"Stock Data: ")
        today_stock=df.iloc[-1:]
        print(today_stock)
        print("##############################################################################")
        df = df.dropna()
        code_list=[]
        for i in range(0,len(df)):
            code_list.append(quote)
        df2=pd.DataFrame(code_list,columns=['Code'])
        df2 = pd.concat([df2, df], axis=1)
        df=df2


        arima_pred, error_arima=ARIMA_ALGO(df)
        lstm_pred, error_lstm=LSTM_ALGO(df)
        df, lr_pred, forecast_set,mean,error_lr=LIN_REG_ALGO(df)
        # Twitter Lookup is no longer free in Twitter's v2 API
        # polarity,tw_list,tw_pol,pos,neg,neutral = retrieving_tweets_polarity(quote)
        polarity, tw_list, tw_pol, pos, neg, neutral = 0, [], "", 0, 0, 0
        
        idea, decision=recommending(df, polarity,today_stock,mean)
        print()
        print("Forecasted Prices for Next 7 days:")
        print(forecast_set)
        today_stock=today_stock.round(2)
       
        return render_template('results.html',quote=quote,arima_pred=round(arima_pred,2),lstm_pred=round(lstm_pred,2),
                               lr_pred=round(lr_pred,2),open_s=today_stock['Open'].to_string(index=False),
                               close_s=today_stock['Close'].to_string(index=False),adj_close=today_stock['Adj Close'].to_string(index=False),
                               tw_list=tw_list,tw_pol=tw_pol,idea=idea,decision=decision,high_s=today_stock['High'].to_string(index=False),
                               low_s=today_stock['Low'].to_string(index=False),vol=today_stock['Volume'].to_string(index=False),
                               forecast_set=forecast_set,error_lr=round(error_lr,2),error_lstm=round(error_lstm,2),error_arima=round(error_arima,2))
if __name__ == '__main__':
   app.run()
   
























