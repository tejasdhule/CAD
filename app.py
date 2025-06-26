import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
from datetime import datetime, timedelta
import time
import threading
from config import NIFTY_100_SYMBOLS, REFRESH_INTERVAL, MAX_CHARTS_PER_PAGE
from data_manager import DataManager
from alert_system import AlertSystem
from indicators import get_latest_signals, get_indicator_summary
from utils import (
    load_stock_data, format_number, format_percentage, get_color_for_value,
    validate_email_config, get_stock_status_summary, clean_old_alerts
)

# Page configuration
st.set_page_config(
    page_title="Nifty 100 Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()

if 'alert_system' not in st.session_state:
    st.session_state.alert_system = AlertSystem()

if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None

def create_stock_chart(symbol, df):
    """Create comprehensive stock chart with all indicators"""
    if df.empty:
        return None
    
    # Create subplots
    fig = sp.make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=(
            f'{symbol.replace(".NS", "")} - Price & Volume',
            'MACD',
            'RSI',
            'MFI'
        )
    )
    
    # Price and Volume
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # Volume bars
    colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7,
            yaxis='y2'
        ),
        row=1, col=1
    )
    
    # MACD
    if 'MACD' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MACD'],
                name='MACD',
                line=dict(color='blue')
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MACD_Signal'],
                name='Signal',
                line=dict(color='red')
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['MACD_Histogram'],
                name='Histogram',
                marker_color='gray',
                opacity=0.6
            ),
            row=2, col=1
        )
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['RSI'],
                name='RSI',
                line=dict(color='purple')
            ),
            row=3, col=1
        )
        
        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=3, col=1)
    
    # MFI
    if 'MFI' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MFI'],
                name='MFI',
                line=dict(color='orange')
            ),
            row=4, col=1
        )
        
        # MFI levels
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=4, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=4, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=4, col=1)
    
    # Update layout
    fig.update_layout(
        height=800,
        title=f"{symbol.replace('.NS', '')} - Technical Analysis",
        xaxis_rangeslider_visible=False,
        showlegend=True
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", secondary_y=True, row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MFI", row=4, col=1, range=[0, 100])
    
    return fig

def display_stock_metrics(symbol, df):
    """Display key metrics for a stock"""
    if df.empty:
        st.warning(f"No data available for {symbol}")
        return
    
    summary = get_indicator_summary(df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Current Price",
            f"₹{format_number(summary['price']['current'])}",
            f"{format_number(summary['price']['change'])} ({format_percentage(summary['price']['change_pct'])}%)",
            delta_color="normal"
        )
    
    with col2:
        macd_status = "🟢 Bullish" if summary['macd']['bullish'] else "🔴 Bearish"
        st.metric(
            "MACD Status",
            macd_status,
            f"Value: {format_number(summary['macd']['value'], 4)}"
        )
    
    with col3:
        rsi_value = summary['rsi']['value']
        rsi_status = "🔴 Overbought" if summary['rsi']['overbought'] else "🟢 Oversold" if summary['rsi']['oversold'] else "⚪ Neutral"
        st.metric(
            "RSI",
            format_number(rsi_value),
            rsi_status
        )
    
    with col4:
        mfi_status = "🟢 Bullish" if summary['mfi']['bullish'] else "🔴 Bearish"
        st.metric(
            "MFI Status",
            mfi_status,
            f"Value: {format_number(summary['mfi']['value'])}"
        )

def scan_for_signals():
    """Scan all stocks for crossover signals"""
    if st.session_state.last_scan_time and (datetime.now() - st.session_state.last_scan_time).seconds < 30:
        return
    
    with st.spinner("Scanning for signals..."):
        signals_found = []
        
        for symbol in NIFTY_100_SYMBOLS:
            df = load_stock_data(symbol)
            if not df.empty:
                signals = get_latest_signals(df)
                
                if signals['macd_crossover'] or signals['mfi_crossover']:
                    signals_found.append({
                        'symbol': symbol,
                        'signals': signals
                    })
                    
                    # Send alert
                    st.session_state.alert_system.check_and_send_alerts(symbol, df)
        
        st.session_state.last_scan_time = datetime.now()
        
        if signals_found:
            st.success(f"Found {len(signals_found)} stocks with active signals!")
            
            for stock in signals_found:
                symbol = stock['symbol']
                signals = stock['signals']
                
                signal_types = []
                if signals['macd_crossover']:
                    signal_types.append("MACD Crossover")
                if signals['mfi_crossover']:
                    signal_types.append("MFI Crossover")
                
                st.info(f"🚨 {symbol.replace('.NS', '')}: {', '.join(signal_types)}")
        else:
            st.info("No active signals detected in current scan.")

def main():
    """Main application"""
    st.title("📈 Nifty 100 Stock Analysis Dashboard")
    st.markdown("Real-time technical analysis with MACD, MFI, RSI indicators and crossover alerts")
    
    # Sidebar
    with st.sidebar:
        st.header("🛠️ Controls")
        
        # Data Management
        st.subheader("Data Management")
        
        if st.button("📥 Download All Historical Data"):
            with st.spinner("Downloading historical data..."):
                success, failed = st.session_state.data_manager.download_all_historical_data()
                st.success(f"Download complete! Success: {success}, Failed: {failed}")
        
        if st.button("🔄 Update Current Data"):
            with st.spinner("Updating current data..."):
                success, failed = st.session_state.data_manager.update_all_current_data()
                st.success(f"Update complete! Success: {success}, Failed: {failed}")
        
        # Alert System
        st.subheader("Alert System")
        
        email_valid, email_msg = validate_email_config()
        if email_valid:
            st.success("✅ Email configured")
        else:
            st.error(f"❌ {email_msg}")
        
        if st.button("📧 Test Email"):
            if st.session_state.alert_system.test_email_configuration():
                st.success("Test email sent successfully!")
            else:
                st.error("Failed to send test email")
        
        # Auto Refresh
        st.subheader("Auto Monitoring")
        
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
        
        if st.button("🔍 Scan for Signals Now"):
            scan_for_signals()
        
        # Data Status
        st.subheader("📊 Data Status")
        status = get_stock_status_summary()
        st.metric("Stocks with Data", f"{status['data_available']}/{status['total_stocks']}")
        
        if status['last_updated']:
            time_diff = datetime.now() - status['last_updated'].to_pydatetime()
            hours_old = time_diff.total_seconds() / 3600
            st.metric("Data Age", f"{hours_old:.1f} hours")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Live Dashboard", "🔍 Stock Analysis", "🚨 Alerts", "📊 Market Overview", "⚙️ Settings"])
    
    with tab1:
        st.header("Live Market Signals")
        
        # Auto refresh mechanism
        if st.session_state.auto_refresh:
            if st.button("🔄 Manual Refresh"):
                scan_for_signals()
                st.rerun()
            st.info("Auto-refresh enabled. Click Manual Refresh to scan for new signals.")
        
        # Recent alerts
        recent_alerts = st.session_state.alert_system.get_recent_alerts(6)
        
        if recent_alerts:
            st.subheader("🚨 Recent Alerts (Last 6 hours)")
            
            for alert in recent_alerts[:5]:  # Show last 5
                with st.expander(f"{alert['symbol'].replace('.NS', '')} - {alert['signal_type'].replace('_', ' ').title()}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Time:** {alert['sent_at'][:19]}")
                    with col2:
                        st.write(f"**Price:** ₹{alert['price']:.2f}")
                    with col3:
                        st.write(f"**Signal Value:** {alert['signal_value']:.4f}")
        else:
            st.info("No recent alerts. System is monitoring...")
        
        # Current signals summary
        st.subheader("📊 Current Market Signals")
        
        signal_summary = {"MACD Bullish": 0, "MFI Bullish": 0, "RSI Oversold": 0, "Volume Surge": 0}
        
        for symbol in NIFTY_100_SYMBOLS[:20]:  # Check first 20 for performance
            df = load_stock_data(symbol)
            if not df.empty:
                signals = get_latest_signals(df)
                
                if signals['macd_crossover']:
                    signal_summary["MACD Bullish"] += 1
                if signals['mfi_crossover']:
                    signal_summary["MFI Bullish"] += 1
                if signals['rsi_value'] and signals['rsi_value'] < 30:
                    signal_summary["RSI Oversold"] += 1
                if signals['volume_surge']:
                    signal_summary["Volume Surge"] += 1
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("MACD Bullish", signal_summary["MACD Bullish"])
        with col2:
            st.metric("MFI Bullish", signal_summary["MFI Bullish"])
        with col3:
            st.metric("RSI Oversold", signal_summary["RSI Oversold"])
        with col4:
            st.metric("Volume Surge", signal_summary["Volume Surge"])
    
    with tab2:
        st.header("Individual Stock Analysis")
        
        # Stock selector
        selected_stock = st.selectbox(
            "Select Stock for Analysis",
            NIFTY_100_SYMBOLS,
            format_func=lambda x: x.replace('.NS', ''),
            key="stock_selector"
        )
        
        if selected_stock:
            df = load_stock_data(selected_stock)
            
            if not df.empty:
                # Display metrics
                display_stock_metrics(selected_stock, df)
                
                st.markdown("---")
                
                # Display chart
                chart = create_stock_chart(selected_stock, df)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                
                # Display recent data
                st.subheader("Recent Data")
                st.dataframe(df.tail(10)[['Open', 'High', 'Low', 'Close', 'Volume', 'MACD', 'RSI', 'MFI']])
                
            else:
                st.warning(f"No data available for {selected_stock}")
                if st.button(f"Download data for {selected_stock}"):
                    with st.spinner("Downloading..."):
                        success = st.session_state.data_manager.download_historical_data(selected_stock)
                        if success:
                            st.success("Data downloaded successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to download data")
    
    with tab3:
        st.header("Alert Management")
        
        # Alert summary
        alert_summary = st.session_state.alert_system.get_alert_summary()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Alerts", alert_summary['total_alerts'])
        with col2:
            st.metric("Today's Alerts", alert_summary['today_alerts'])
        with col3:
            if alert_summary['most_active_stock']:
                st.metric("Most Active Stock", alert_summary['most_active_stock'].replace('.NS', ''))
        
        st.markdown("---")
        
        # Recent alerts table
        st.subheader("Recent Alerts")
        
        recent_alerts = st.session_state.alert_system.get_recent_alerts(72)  # Last 3 days
        
        if recent_alerts:
            alert_df = pd.DataFrame(recent_alerts)
            alert_df['sent_at'] = pd.to_datetime(alert_df['sent_at']).dt.strftime('%Y-%m-%d %H:%M')
            alert_df['symbol'] = alert_df['symbol'].str.replace('.NS', '')
            alert_df['signal_type'] = alert_df['signal_type'].str.replace('_', ' ').str.title()
            
            st.dataframe(
                alert_df[['sent_at', 'symbol', 'signal_type', 'price', 'signal_value']].rename(columns={
                    'sent_at': 'Time',
                    'symbol': 'Stock',
                    'signal_type': 'Signal Type',
                    'price': 'Price (₹)',
                    'signal_value': 'Signal Value'
                }),
                use_container_width=True
            )
        else:
            st.info("No recent alerts")
        
        # Alert controls
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Clear Alert Log"):
                if st.session_state.alert_system.clear_alert_log():
                    st.success("Alert log cleared!")
                    st.rerun()
        
        with col2:
            if st.button("🗑️ Clean Old Alerts"):
                cleaned = clean_old_alerts(7)  # Clean alerts older than 7 days
                st.success(f"Cleaned {cleaned} old alerts")
                st.rerun()
    
    with tab4:
        st.header("Market Overview")
        
        # Market summary
        st.subheader("Nifty 100 Market Summary")
        
        # Get data for all stocks
        market_data = []
        
        progress_bar = st.progress(0)
        
        for i, symbol in enumerate(NIFTY_100_SYMBOLS[:50]):  # First 50 for performance
            df = load_stock_data(symbol)
            
            if not df.empty:
                summary = get_indicator_summary(df)
                
                market_data.append({
                    'Stock': symbol.replace('.NS', ''),
                    'Price': summary['price']['current'],
                    'Change %': summary['price']['change_pct'],
                    'MACD': 'Bullish' if summary['macd']['bullish'] else 'Bearish',
                    'RSI': summary['rsi']['value'],
                    'MFI': summary['mfi']['value'],
                    'Volume Surge': 'Yes' if summary['volume']['surge'] else 'No'
                })
            
            progress_bar.progress((i + 1) / 50)
        
        if market_data:
            market_df = pd.DataFrame(market_data)
            
            # Format the dataframe
            market_df['Change %'] = market_df['Change %'].round(2)
            market_df['RSI'] = market_df['RSI'].round(2)
            market_df['MFI'] = market_df['MFI'].round(2)
            
            st.dataframe(market_df, use_container_width=True)
            
            # Market statistics
            st.subheader("Market Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                bullish_macd = len(market_df[market_df['MACD'] == 'Bullish'])
                st.metric("MACD Bullish", f"{bullish_macd}/{len(market_df)}")
            
            with col2:
                avg_rsi = market_df['RSI'].mean()
                st.metric("Average RSI", f"{avg_rsi:.1f}")
            
            with col3:
                avg_mfi = market_df['MFI'].mean()
                st.metric("Average MFI", f"{avg_mfi:.1f}")
            
            with col4:
                volume_surge = len(market_df[market_df['Volume Surge'] == 'Yes'])
                st.metric("Volume Surge", f"{volume_surge}/{len(market_df)}")
        
    with tab5:
        st.header("Settings & Configuration")
        
        # Email settings
        st.subheader("📧 Email Configuration")
        
        email_valid, email_msg = validate_email_config()
        
        if email_valid:
            st.success(f"✅ {email_msg}")
        else:
            st.error(f"❌ {email_msg}")
        
        st.info("""
        **Email Setup Instructions:**
        1. Set environment variable `EMAIL_USER` with your Gmail address
        2. Set environment variable `EMAIL_PASSWORD` with your Gmail app password
        3. Set environment variable `EMAIL_RECIPIENTS` with comma-separated recipient emails
        
        **Gmail App Password Setup:**
        1. Enable 2-factor authentication on your Gmail account
        2. Go to Google Account settings → Security → App passwords
        3. Generate an app password for this application
        """)
        
        # System settings
        st.subheader("⚙️ System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Refresh Interval:** {REFRESH_INTERVAL} seconds")
            st.info(f"**Stocks Monitored:** {len(NIFTY_100_SYMBOLS)}")
            st.info(f"**Charts Per Page:** {MAX_CHARTS_PER_PAGE}")
        
        with col2:
            st.info(f"**MACD Parameters:** {12}, {26}, {9}")
            st.info(f"**RSI Period:** {14}")
            st.info(f"**MFI Period:** {14}")
        
        # Data management
        st.subheader("💾 Data Management")
        
        data_status = st.session_state.data_manager.get_data_status()
        
        available_count = sum(1 for status in data_status.values() if status['status'] == 'Available')
        
        st.metric("Data Coverage", f"{available_count}/{len(NIFTY_100_SYMBOLS)} stocks")
        
        if st.button("🔍 Check Data Freshness"):
            freshness = st.session_state.data_manager.check_data_freshness()
            
            fresh_count = sum(1 for f in freshness.values() if f == 'Fresh')
            recent_count = sum(1 for f in freshness.values() if f == 'Recent')
            stale_count = sum(1 for f in freshness.values() if f == 'Stale')
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Fresh (< 4h)", fresh_count)
            with col2:
                st.metric("Recent (< 24h)", recent_count)
            with col3:
                st.metric("Stale (> 24h)", stale_count)

if __name__ == "__main__":
    main()
