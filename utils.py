import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
import streamlit as st

def create_data_folder():
    """Create data folder if it doesn't exist"""
    if not os.path.exists("stock_data"):
        os.makedirs("stock_data")
    if not os.path.exists("stock_data/historical"):
        os.makedirs("stock_data/historical")
    if not os.path.exists("stock_data/alerts"):
        os.makedirs("stock_data/alerts")

def get_file_path(symbol, data_type="historical"):
    """Get file path for stock data"""
    return f"stock_data/{data_type}/{symbol.replace('.NS', '')}.csv"

def load_stock_data(symbol):
    """Load stock data from CSV file"""
    file_path = get_file_path(symbol)
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data for {symbol}: {str(e)}")
        return pd.DataFrame()

def save_stock_data(symbol, df):
    """Save stock data to CSV file"""
    file_path = get_file_path(symbol)
    try:
        df.to_csv(file_path)
        return True
    except Exception as e:
        st.error(f"Error saving data for {symbol}: {str(e)}")
        return False

def load_alert_log():
    """Load alert log from JSON file"""
    log_file = "stock_data/alerts/alert_log.json"
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Error loading alert log: {str(e)}")
        return []

def save_alert_log(alerts):
    """Save alert log to JSON file"""
    log_file = "stock_data/alerts/alert_log.json"
    try:
        with open(log_file, 'w') as f:
            json.dump(alerts, f, indent=2, default=str)
        return True
    except Exception as e:
        st.error(f"Error saving alert log: {str(e)}")
        return False

def rate_limit_delay():
    """Add delay to respect rate limits"""
    time.sleep(0.5)

def format_number(value, decimals=2):
    """Format number for display"""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}"

def format_percentage(value, decimals=2):
    """Format percentage for display"""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}%"

def get_color_for_value(value, positive_color="#00C851", negative_color="#FF4444"):
    """Get color based on positive/negative value"""
    if pd.isna(value):
        return "#6C757D"
    return positive_color if value > 0 else negative_color

def validate_email_config():
    """Validate email configuration"""
    from config import EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENTS
    if not EMAIL_USER or not EMAIL_PASSWORD:
        return False, "Email credentials not configured"
    if not EMAIL_RECIPIENTS or not any(EMAIL_RECIPIENTS):
        return False, "No email recipients configured"
    return True, "Email configuration valid"

def clean_old_alerts(days=7):
    """Clean alerts older than specified days"""
    alerts = load_alert_log()
    cutoff_date = datetime.now() - timedelta(days=days)
    
    cleaned_alerts = [
        alert for alert in alerts
        if datetime.fromisoformat(alert.get('timestamp', '1970-01-01')) > cutoff_date
    ]
    
    save_alert_log(cleaned_alerts)
    return len(alerts) - len(cleaned_alerts)

def get_stock_status_summary():
    """Get summary of stock data status"""
    from config import NIFTY_100_SYMBOLS
    
    status = {
        'total_stocks': len(NIFTY_100_SYMBOLS),
        'data_available': 0,
        'last_updated': None,
        'missing_data': []
    }
    
    for symbol in NIFTY_100_SYMBOLS:
        df = load_stock_data(symbol)
        if not df.empty:
            status['data_available'] += 1
            if status['last_updated'] is None or df.index[-1] > pd.to_datetime(status['last_updated']):
                status['last_updated'] = df.index[-1]
        else:
            status['missing_data'].append(symbol)
    
    return status
