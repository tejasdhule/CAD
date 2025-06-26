import yfinance as yf
import pandas as pd
import streamlit as st
import time
from datetime import datetime, timedelta
from config import NIFTY_100_SYMBOLS, HISTORICAL_PERIOD, REQUEST_DELAY, BATCH_SIZE
from utils import save_stock_data, load_stock_data, rate_limit_delay, create_data_folder
from indicators import calculate_all_indicators

class DataManager:
    def __init__(self):
        create_data_folder()
        self.last_update = {}
        
    def download_historical_data(self, symbol, progress_callback=None):
        """Download historical data for a single stock"""
        try:
            # Rate limiting
            rate_limit_delay()
            
            # Download data
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=HISTORICAL_PERIOD, interval="1h")
            
            if df.empty:
                st.warning(f"No data available for {symbol}")
                return False
            
            # Resample to 4-hour data
            df_4h = df.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Calculate indicators
            df_4h = calculate_all_indicators(df_4h)
            
            # Save data
            success = save_stock_data(symbol, df_4h)
            
            if success:
                self.last_update[symbol] = datetime.now()
                if progress_callback:
                    progress_callback(symbol, True)
                return True
            else:
                if progress_callback:
                    progress_callback(symbol, False)
                return False
                
        except Exception as e:
            st.error(f"Error downloading data for {symbol}: {str(e)}")
            if progress_callback:
                progress_callback(symbol, False)
            return False
    
    def download_all_historical_data(self):
        """Download historical data for all Nifty 100 stocks"""
        st.info("Starting historical data download for all Nifty 100 stocks...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        successful = 0
        failed = 0
        
        def update_progress(symbol, success):
            nonlocal successful, failed
            if success:
                successful += 1
            else:
                failed += 1
            
            total_processed = successful + failed
            progress = total_processed / len(NIFTY_100_SYMBOLS)
            progress_bar.progress(progress)
            status_text.text(f"Processed: {total_processed}/{len(NIFTY_100_SYMBOLS)} | Success: {successful} | Failed: {failed}")
        
        # Process stocks in batches
        for i in range(0, len(NIFTY_100_SYMBOLS), BATCH_SIZE):
            batch = NIFTY_100_SYMBOLS[i:i+BATCH_SIZE]
            
            for symbol in batch:
                self.download_historical_data(symbol, update_progress)
            
            # Longer delay between batches
            if i + BATCH_SIZE < len(NIFTY_100_SYMBOLS):
                time.sleep(2)
        
        progress_bar.progress(1.0)
        status_text.text(f"Download complete! Success: {successful} | Failed: {failed}")
        
        return successful, failed
    
    def update_current_data(self, symbol):
        """Update current data for a single stock"""
        try:
            # Load existing data
            df = load_stock_data(symbol)
            
            if df.empty:
                return False
            
            # Get latest timestamp
            last_timestamp = df.index[-1]
            
            # Only update if data is older than 4 hours
            if datetime.now() - last_timestamp.to_pydatetime() < timedelta(hours=4):
                return True
            
            # Rate limiting
            rate_limit_delay()
            
            # Download recent data
            ticker = yf.Ticker(symbol)
            recent_df = ticker.history(period="5d", interval="1h")
            
            if recent_df.empty:
                return False
            
            # Resample to 4-hour data
            recent_4h = recent_df.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Merge with existing data
            combined_df = pd.concat([df, recent_4h[recent_4h.index > last_timestamp]])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            
            # Recalculate indicators
            combined_df = calculate_all_indicators(combined_df)
            
            # Save updated data
            success = save_stock_data(symbol, combined_df)
            
            if success:
                self.last_update[symbol] = datetime.now()
            
            return success
            
        except Exception as e:
            st.error(f"Error updating data for {symbol}: {str(e)}")
            return False
    
    def update_all_current_data(self):
        """Update current data for all stocks"""
        successful = 0
        failed = 0
        
        for symbol in NIFTY_100_SYMBOLS:
            if self.update_current_data(symbol):
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def get_data_status(self):
        """Get status of all stock data"""
        status = {}
        
        for symbol in NIFTY_100_SYMBOLS:
            df = load_stock_data(symbol)
            
            if df.empty:
                status[symbol] = {
                    'status': 'No Data',
                    'last_update': None,
                    'records': 0
                }
            else:
                status[symbol] = {
                    'status': 'Available',
                    'last_update': df.index[-1],
                    'records': len(df)
                }
        
        return status
    
    def force_refresh_stock(self, symbol):
        """Force refresh data for a specific stock"""
        return self.download_historical_data(symbol)
    
    def get_stock_data_with_indicators(self, symbol):
        """Get stock data with all indicators calculated"""
        df = load_stock_data(symbol)
        
        if df.empty:
            return df
        
        # Ensure indicators are calculated
        if 'MACD' not in df.columns:
            df = calculate_all_indicators(df)
            save_stock_data(symbol, df)
        
        return df
    
    def get_latest_prices(self):
        """Get latest prices for all stocks"""
        prices = {}
        
        for symbol in NIFTY_100_SYMBOLS:
            df = load_stock_data(symbol)
            if not df.empty:
                prices[symbol] = {
                    'price': df['Close'].iloc[-1],
                    'timestamp': df.index[-1]
                }
        
        return prices
    
    def check_data_freshness(self):
        """Check how fresh the data is for all stocks"""
        freshness = {}
        now = datetime.now()
        
        for symbol in NIFTY_100_SYMBOLS:
            df = load_stock_data(symbol)
            
            if df.empty:
                freshness[symbol] = 'No Data'
            else:
                last_update = df.index[-1].to_pydatetime()
                hours_old = (now - last_update).total_seconds() / 3600
                
                if hours_old < 4:
                    freshness[symbol] = 'Fresh'
                elif hours_old < 24:
                    freshness[symbol] = 'Recent'
                else:
                    freshness[symbol] = 'Stale'
        
        return freshness
