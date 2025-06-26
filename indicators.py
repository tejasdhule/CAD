import pandas as pd
import numpy as np
from config import MACD_FAST, MACD_SLOW, MACD_SIGNAL, RSI_PERIOD, MFI_PERIOD, VOLUME_MA_SHORT, VOLUME_MA_LONG

def calculate_macd(df):
    """Calculate MACD indicator using pure pandas"""
    try:
        close = df['Close']
        
        # Calculate EMAs
        ema_fast = close.ewm(span=MACD_FAST).mean()
        ema_slow = close.ewm(span=MACD_SLOW).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        signal_line = macd_line.ewm(span=MACD_SIGNAL).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        df['MACD'] = macd_line
        df['MACD_Signal'] = signal_line
        df['MACD_Histogram'] = histogram
        
        # Calculate crossover signals
        df['MACD_Crossover'] = np.where(
            (df['MACD'] > df['MACD_Signal']) & 
            (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1)), 
            1, 0
        )
        
        return df
    except Exception as e:
        print(f"Error calculating MACD: {str(e)}")
        return df

def calculate_rsi(df):
    """Calculate RSI indicator using pure pandas"""
    try:
        close = df['Close']
        delta = close.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gain = gain.rolling(window=RSI_PERIOD).mean()
        avg_loss = loss.rolling(window=RSI_PERIOD).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        df['RSI'] = rsi
        return df
    except Exception as e:
        print(f"Error calculating RSI: {str(e)}")
        return df

def calculate_mfi(df):
    """Calculate Money Flow Index using pure pandas"""
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        volume = df['Volume']
        
        # Calculate typical price
        typical_price = (high + low + close) / 3
        
        # Calculate money flow
        money_flow = typical_price * volume
        
        # Calculate positive and negative money flows
        positive_flow = pd.Series(index=df.index, dtype=float)
        negative_flow = pd.Series(index=df.index, dtype=float)
        
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = money_flow.iloc[i]
                negative_flow.iloc[i] = 0
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                positive_flow.iloc[i] = 0
                negative_flow.iloc[i] = money_flow.iloc[i]
            else:
                positive_flow.iloc[i] = 0
                negative_flow.iloc[i] = 0
        
        # Calculate 14-period sums
        positive_flow_sum = positive_flow.rolling(window=MFI_PERIOD).sum()
        negative_flow_sum = negative_flow.rolling(window=MFI_PERIOD).sum()
        
        # Calculate money flow ratio and MFI
        money_flow_ratio = positive_flow_sum / negative_flow_sum
        mfi = 100 - (100 / (1 + money_flow_ratio))
        
        df['MFI'] = mfi
        
        # Calculate MFI crossover signals (above 50 line)
        df['MFI_Crossover'] = np.where(
            (df['MFI'] > 50) & (df['MFI'].shift(1) <= 50), 
            1, 0
        )
        
        return df
    except Exception as e:
        print(f"Error calculating MFI: {str(e)}")
        return df

def calculate_volume_indicators(df):
    """Calculate volume-based indicators"""
    try:
        df['Volume_MA_Short'] = df['Volume'].rolling(window=VOLUME_MA_SHORT).mean()
        df['Volume_MA_Long'] = df['Volume'].rolling(window=VOLUME_MA_LONG).mean()
        
        # Volume surge detection
        df['Volume_Surge'] = np.where(
            df['Volume'] > df['Volume_MA_Short'] * 1.5, 1, 0
        )
        
        return df
    except Exception as e:
        print(f"Error calculating volume indicators: {str(e)}")
        return df

def calculate_all_indicators(df):
    """Calculate all technical indicators"""
    if df.empty:
        return df
    
    try:
        df = calculate_macd(df)
        df = calculate_rsi(df)
        df = calculate_mfi(df)
        df = calculate_volume_indicators(df)
        
        return df
    except Exception as e:
        print(f"Error calculating indicators: {str(e)}")
        return df

def get_latest_signals(df):
    """Get latest crossover signals"""
    if df.empty or len(df) < 2:
        return {
            'macd_crossover': False,
            'mfi_crossover': False,
            'macd_value': None,
            'mfi_value': None,
            'rsi_value': None,
            'volume_surge': False
        }
    
    latest = df.iloc[-1]
    
    return {
        'macd_crossover': bool(latest.get('MACD_Crossover', 0)),
        'mfi_crossover': bool(latest.get('MFI_Crossover', 0)),
        'macd_value': latest.get('MACD', None),
        'mfi_value': latest.get('MFI', None),
        'rsi_value': latest.get('RSI', None),
        'volume_surge': bool(latest.get('Volume_Surge', 0)),
        'close_price': latest.get('Close', None),
        'timestamp': latest.name if hasattr(latest, 'name') else None
    }

def detect_crossover_signals(df):
    """Detect all types of crossover signals"""
    signals = []
    
    if df.empty or len(df) < 2:
        return signals
    
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    # MACD bullish crossover
    if (latest.get('MACD', 0) > latest.get('MACD_Signal', 0) and 
        previous.get('MACD', 0) <= previous.get('MACD_Signal', 0)):
        signals.append({
            'type': 'MACD_BULLISH_CROSSOVER',
            'value': latest.get('MACD', 0),
            'signal_value': latest.get('MACD_Signal', 0),
            'timestamp': latest.name if hasattr(latest, 'name') else None
        })
    
    # MFI bullish crossover (crossing above 50)
    if (latest.get('MFI', 0) > 50 and previous.get('MFI', 0) <= 50):
        signals.append({
            'type': 'MFI_BULLISH_CROSSOVER',
            'value': latest.get('MFI', 0),
            'signal_value': 50,
            'timestamp': latest.name if hasattr(latest, 'name') else None
        })
    
    # Additional signals can be added here
    # RSI oversold recovery
    if (latest.get('RSI', 0) > 30 and previous.get('RSI', 0) <= 30):
        signals.append({
            'type': 'RSI_OVERSOLD_RECOVERY',
            'value': latest.get('RSI', 0),
            'signal_value': 30,
            'timestamp': latest.name if hasattr(latest, 'name') else None
        })
    
    return signals

def get_indicator_summary(df):
    """Get summary of all indicators"""
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    summary = {
        'price': {
            'current': latest.get('Close', 0),
            'change': latest.get('Close', 0) - df.iloc[-2].get('Close', 0) if len(df) > 1 else 0,
            'change_pct': ((latest.get('Close', 0) - df.iloc[-2].get('Close', 0)) / df.iloc[-2].get('Close', 1) * 100) if len(df) > 1 else 0
        },
        'macd': {
            'value': latest.get('MACD', None),
            'signal': latest.get('MACD_Signal', None),
            'histogram': latest.get('MACD_Histogram', None),
            'bullish': latest.get('MACD', 0) > latest.get('MACD_Signal', 0)
        },
        'rsi': {
            'value': latest.get('RSI', None),
            'overbought': latest.get('RSI', 0) > 70,
            'oversold': latest.get('RSI', 0) < 30
        },
        'mfi': {
            'value': latest.get('MFI', None),
            'overbought': latest.get('MFI', 0) > 80,
            'oversold': latest.get('MFI', 0) < 20,
            'bullish': latest.get('MFI', 0) > 50
        },
        'volume': {
            'current': latest.get('Volume', 0),
            'ma_short': latest.get('Volume_MA_Short', None),
            'ma_long': latest.get('Volume_MA_Long', None),
            'surge': latest.get('Volume_Surge', False)
        }
    }
    
    return summary
