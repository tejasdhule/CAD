import smtplib
import pandas as pd
from datetime import datetime
import streamlit as st
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENTS
from utils import load_alert_log, save_alert_log
from indicators import detect_crossover_signals, get_latest_signals

class AlertSystem:
    def __init__(self):
        self.alert_log = load_alert_log()
        
    def send_email_alert(self, subject, message):
        """Send email alert"""
        try:
            if not EMAIL_USER or not EMAIL_PASSWORD:
                st.warning("Email credentials not configured")
                return False
            
            if not EMAIL_RECIPIENTS:
                st.warning("No email recipients configured")
                return False
            
            # Simple email format without MIME
            email_message = f"Subject: {subject}\nFrom: {EMAIL_USER}\nTo: {', '.join(EMAIL_RECIPIENTS)}\nContent-Type: text/html\n\n{message}"
            
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            
            server.sendmail(EMAIL_USER, EMAIL_RECIPIENTS, email_message)
            server.quit()
            
            return True
            
        except Exception as e:
            st.error(f"Failed to send email: {str(e)}")
            return False
    
    def create_alert_message(self, symbol, signals, stock_data):
        """Create formatted alert message"""
        if stock_data.empty:
            return None
        
        latest = stock_data.iloc[-1]
        
        message = f"""
        <html>
        <body>
        <h2>🚨 Stock Alert: {symbol.replace('.NS', '')}</h2>
        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Current Price:</strong> ₹{latest['Close']:.2f}</p>
        
        <h3>Signals Detected:</h3>
        <ul>
        """
        
        for signal in signals:
            if signal['type'] == 'MACD_BULLISH_CROSSOVER':
                message += f"<li>📈 <strong>MACD Bullish Crossover</strong><br>MACD: {signal['value']:.4f} | Signal: {signal['signal_value']:.4f}</li>"
            elif signal['type'] == 'MFI_BULLISH_CROSSOVER':
                message += f"<li>💰 <strong>MFI Bullish Crossover</strong><br>MFI: {signal['value']:.2f} (crossed above 50)</li>"
            elif signal['type'] == 'RSI_OVERSOLD_RECOVERY':
                message += f"<li>🔄 <strong>RSI Oversold Recovery</strong><br>RSI: {signal['value']:.2f} (crossed above 30)</li>"
        
        message += """
        </ul>
        
        <h3>Current Indicator Values:</h3>
        <table border="1" style="border-collapse: collapse;">
        <tr>
            <td><strong>Indicator</strong></td>
            <td><strong>Value</strong></td>
            <td><strong>Status</strong></td>
        </tr>
        """
        
        # Add indicator values
        if 'MACD' in latest:
            macd_status = "Bullish" if latest['MACD'] > latest['MACD_Signal'] else "Bearish"
            message += f"<tr><td>MACD</td><td>{latest['MACD']:.4f}</td><td>{macd_status}</td></tr>"
        
        if 'RSI' in latest:
            rsi_status = "Overbought" if latest['RSI'] > 70 else "Oversold" if latest['RSI'] < 30 else "Neutral"
            message += f"<tr><td>RSI</td><td>{latest['RSI']:.2f}</td><td>{rsi_status}</td></tr>"
        
        if 'MFI' in latest:
            mfi_status = "Overbought" if latest['MFI'] > 80 else "Oversold" if latest['MFI'] < 20 else "Neutral"
            message += f"<tr><td>MFI</td><td>{latest['MFI']:.2f}</td><td>{mfi_status}</td></tr>"
        
        message += """
        </table>
        
        <p><em>This is an automated alert from your Stock Analysis Dashboard.</em></p>
        </body>
        </html>
        """
        
        return message
    
    def check_and_send_alerts(self, symbol, stock_data):
        """Check for signals and send alerts if needed"""
        if stock_data.empty:
            return False
        
        # Detect signals
        signals = detect_crossover_signals(stock_data)
        
        if not signals:
            return False
        
        # Check if we've already sent alerts for these signals
        latest_timestamp = stock_data.index[-1]
        
        for signal in signals:
            alert_key = f"{symbol}_{signal['type']}_{latest_timestamp}"
            
            # Check if alert already sent
            if any(alert.get('key') == alert_key for alert in self.alert_log):
                continue
            
            # Create and send alert
            message = self.create_alert_message(symbol, [signal], stock_data)
            subject = f"Stock Alert: {symbol.replace('.NS', '')} - {signal['type'].replace('_', ' ').title()}"
            
            if self.send_email_alert(subject, message):
                # Log the alert
                alert_record = {
                    'key': alert_key,
                    'symbol': symbol,
                    'signal_type': signal['type'],
                    'timestamp': latest_timestamp.isoformat() if hasattr(latest_timestamp, 'isoformat') else str(latest_timestamp),
                    'sent_at': datetime.now().isoformat(),
                    'price': stock_data['Close'].iloc[-1],
                    'signal_value': signal['value']
                }
                
                self.alert_log.append(alert_record)
                save_alert_log(self.alert_log)
                
                return True
        
        return False
    
    def get_recent_alerts(self, hours=24):
        """Get recent alerts within specified hours"""
        if not self.alert_log:
            return []
        
        cutoff_time = datetime.now() - pd.Timedelta(hours=hours)
        
        recent_alerts = []
        for alert in self.alert_log:
            try:
                alert_time = datetime.fromisoformat(alert['sent_at'])
                if alert_time > cutoff_time:
                    recent_alerts.append(alert)
            except:
                continue
        
        return sorted(recent_alerts, key=lambda x: x['sent_at'], reverse=True)
    
    def get_alert_summary(self):
        """Get summary of alert activity"""
        if not self.alert_log:
            return {
                'total_alerts': 0,
                'today_alerts': 0,
                'most_active_stock': None,
                'recent_alerts': []
            }
        
        today = datetime.now().date()
        today_alerts = 0
        stock_counts = {}
        
        for alert in self.alert_log:
            try:
                alert_date = datetime.fromisoformat(alert['sent_at']).date()
                if alert_date == today:
                    today_alerts += 1
                
                symbol = alert['symbol']
                stock_counts[symbol] = stock_counts.get(symbol, 0) + 1
            except:
                continue
        
        most_active_stock = max(stock_counts.items(), key=lambda x: x[1])[0] if stock_counts else None
        
        return {
            'total_alerts': len(self.alert_log),
            'today_alerts': today_alerts,
            'most_active_stock': most_active_stock,
            'recent_alerts': self.get_recent_alerts(24)
        }
    
    def test_email_configuration(self):
        """Test email configuration"""
        try:
            subject = "Test Alert - Stock Dashboard"
            message = """
            <html>
            <body>
            <h2>📧 Test Alert</h2>
            <p>This is a test email from your Stock Analysis Dashboard.</p>
            <p>If you receive this email, your email configuration is working correctly.</p>
            <p><em>Time: {}</em></p>
            </body>
            </html>
            """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            return self.send_email_alert(subject, message)
        except Exception as e:
            st.error(f"Email test failed: {str(e)}")
            return False
    
    def clear_alert_log(self):
        """Clear all alerts from log"""
        self.alert_log = []
        return save_alert_log(self.alert_log)
