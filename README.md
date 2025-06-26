# Nifty Stock Analysis Dashboard

A Streamlit-based real-time stock analysis dashboard for monitoring 25 major Indian stocks with technical indicators and automated alert system.

## Quick Deploy to Streamlit Cloud

1. Upload these files to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Choose `app.py` as main file
5. Deploy!

## Features

- **Real-time Analysis**: Monitors 25 selected Indian stocks using Yahoo Finance data
- **Technical Indicators**: MACD, RSI, MFI calculated on 4-hour timeframes
- **Signal Detection**: Automatic detection of bullish crossovers and trading opportunities
- **Email Alerts**: Automated notifications when positive signals are detected
- **Interactive Charts**: Plotly-based charts with volume analysis and indicator overlays

## Optional: Email Alert Configuration

Add these secrets in Streamlit Cloud dashboard:
```
EMAIL_USER = your-gmail@gmail.com
EMAIL_PASSWORD = your-gmail-app-password
EMAIL_RECIPIENTS = recipient1@gmail.com,recipient2@gmail.com
```

## Monitored Stocks

Reliance Industries, HDFC Bank, TCS, Bharti Airtel, ICICI Bank, State Bank of India, Infosys, Life Insurance Corp, Bajaj Finance, Hindustan Unilever, ITC, Larsen & Toubro, HCL Technologies, Kotak Mahindra Bank, Maruti Suzuki, Sun Pharma, Mahindra & Mahindra, Axis Bank, UltraTech Cement, Titan Company, Bajaj Finserv, NTPC, Hindustan Aeronautics, ONGC, Adani Ports

## Technical Analysis

- **MACD (12,26,9)**: Moving Average Convergence Divergence for trend analysis
- **RSI (14)**: Relative Strength Index for momentum analysis  
- **MFI (14)**: Money Flow Index for volume-weighted momentum
- **4-Hour Timeframe**: Hourly data resampled to 4-hour candles for swing trading