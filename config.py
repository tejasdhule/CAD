import os

# Stock configuration
NIFTY_100_SYMBOLS = [
    "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "BHARTIARTL.NS", "ICICIBANK.NS",
    "SBIN.NS", "INFY.NS", "LICI.NS", "BAJFINANCE.NS", "HINDUNILVR.NS",
    "ITC.NS", "LT.NS", "HCLTECH.NS", "KOTAKBANK.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "M&M.NS", "AXISBANK.NS", "ULTRACEMCO.NS", "TITAN.NS",
    "BAJAJFINSV.NS", "NTPC.NS", "HAL.NS", "ONGC.NS", "ADANIPORTS.NS"
]

# Technical indicator parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
MFI_PERIOD = 14
VOLUME_MA_SHORT = 20
VOLUME_MA_LONG = 50

# Data configuration
DATA_FOLDER = "stock_data"
TIMEFRAME = "4h"
HISTORICAL_PERIOD = "6mo"  # 6 months of historical data

# Email configuration
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587

# API rate limiting
REQUEST_DELAY = 0.5  # seconds between requests
BATCH_SIZE = 10  # number of stocks to process in each batch

# Dashboard configuration
REFRESH_INTERVAL = 60  # seconds
MAX_CHARTS_PER_PAGE = 6

# Environment variables
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else []
