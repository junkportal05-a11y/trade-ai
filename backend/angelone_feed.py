"""
AngelOne SmartAPI Integration Module
Replaces Upstox as the unified data & execution provider
"""

import os
import json
import logging
import pyotp
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from SmartApi import SmartConnect
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class AngelOneFeed:
    """
    Unified wrapper for AngelOne SmartAPI
    Handles: Authentication, Market Data, Historical Data, Order Execution
    """
    
    def __init__(self):
        self.smart_api = None
        self.session_token = None
        self.refresh_token = None
        self.feed_token = None
        self.client_code = None
        self.instruments = {}
        self.instruments_file = Path(os.path.join(os.path.dirname(__file__), "angelone_instruments.json"))
        
    # ==========================================
    # AUTHENTICATION
    # ==========================================
    
    def login(self, api_key: str, client_code: str, pin: str, totp_secret: str) -> Dict:
        """
        Authenticate with AngelOne using TOTP-based login
        """
        try:
            # Initialize SmartConnect
            self.smart_api = SmartConnect(api_key=api_key)
            self.client_code = client_code
            
            # Generate TOTP
            totp = pyotp.TOTP(totp_secret)
            totp_code = totp.now()
            
            logger.info(f"Attempting AngelOne login for client: {client_code}")
            
            # Generate session
            session_data = self.smart_api.generateSession(
                clientCode=client_code,
                password=pin,
                totp=totp_code
            )
            
            if not session_data or session_data['status'] == False:
                error_msg = session_data.get('message', 'Unknown error')
                logger.error(f"AngelOne login failed: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # Extract tokens
            data = session_data['data']
            self.session_token = data['jwtToken']
            self.refresh_token = data['refreshToken']
            self.feed_token = data['feedToken']
            
            # Set access token for subsequent calls
            self.smart_api.setAccessToken(self.session_token)
            
            logger.info("✅ AngelOne authentication successful")
            
            # Download instrument master
            self._download_instrument_master()
            
            return {
                "status": "success",
                "session_token": self.session_token,
                "refresh_token": self.refresh_token,
                "feed_token": self.feed_token,
                "client_code": client_code
            }
            
        except Exception as e:
            logger.error(f"AngelOne login exception: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def ensure_api_client(self) -> bool:
        """
        Restore API client state if server restarted but session exists in DB
        """
        if self.smart_api and self.session_token:
            return True
        try:
            import db
            session = db.get_angelone_session()
            if session and session.get('api_key'):
                self.smart_api = SmartConnect(api_key=session['api_key'])
                self.client_code = session['client_code']
                self.session_token = session['session_token']
                self.refresh_token = session['refresh_token']
                self.feed_token = session['feed_token']
                self.smart_api.setAccessToken(self.session_token)
                return True
        except Exception as e:
            logger.error(f"Error restoring AngelOne API client: {e}")
        return False

    def refresh_session(self, refresh_token: str) -> bool:
        """
        Refresh expired session using refresh token
        """
        try:
            if not self.ensure_api_client():
                return False
            response = self.smart_api.generateToken(refresh_token)
            
            if response['status']:
                self.session_token = response['data']['jwtToken']
                self.smart_api.setAccessToken(self.session_token)
                logger.info("✅ Session refreshed successfully")
                return True
            else:
                logger.error(f"Session refresh failed: {response['message']}")
                return False
                
        except Exception as e:
            logger.error(f"Session refresh exception: {str(e)}")
            return False
    
    def is_authorized(self) -> bool:
        """
        Check if current session is valid
        """
        if not self.ensure_api_client():
            return False
        
        try:
            # Test API call to verify session
            profile = self.smart_api.getProfile(self.refresh_token)
            return profile['status'] == True
        except:
            return False
    
    # ==========================================
    # INSTRUMENT MASTER
    # ==========================================
    
    def _download_instrument_master(self) -> bool:
        """
        Download and cache AngelOne instrument master
        """
        try:
            logger.info("Downloading AngelOne instrument master...")
            
            import requests
            
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                instruments = response.json()
                
                # Filter for NSE equity only
                nse_instruments = [
                    inst for inst in instruments 
                    if inst['exch_seg'] == 'NSE' and inst['symbol'].endswith('-EQ')
                ]
                
                # Create symbol → token mapping
                self.instruments = {
                    inst['symbol']: {
                        'token': inst['token'],
                        'symbol': inst['symbol'],
                        'name': inst['name'],
                        'lotsize': inst['lotsize'],
                        'tick_size': inst['tick_size']
                    }
                    for inst in nse_instruments
                }
                
                # Save to disk
                with open(self.instruments_file, 'w') as f:
                    json.dump(self.instruments, f, indent=2)
                
                logger.info(f"✅ Cached {len(self.instruments)} NSE instruments")
                return True
            else:
                logger.error(f"Failed to download instruments: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Instrument download error: {str(e)}")
            return False
    
    def get_instrument_token(self, symbol: str) -> Optional[str]:
        """
        Get AngelOne token for a symbol
        """
        if not self.instruments:
            if not self.instruments_file.exists():
                self._download_instrument_master()
            if self.instruments_file.exists():
                with open(self.instruments_file, 'r') as f:
                    self.instruments = json.load(f)
        
        # Normalize symbol (remove -EQ suffix or .NS if present)
        clean_symbol = symbol.replace("-EQ", "").replace(".NS", "").upper() + "-EQ"
        
        if clean_symbol in self.instruments:
            return self.instruments[clean_symbol]['token']
            
        # Try raw just in case
        if symbol.upper() in self.instruments:
            return self.instruments[symbol.upper()]['token']
            
        # Try without any suffix
        clean_base = symbol.replace("-EQ", "").replace(".NS", "").upper()
        if clean_base in self.instruments:
             return self.instruments[clean_base]['token']
        
        logger.warning(f"Symbol {symbol} not found in instrument master")
        return None
    
    # ==========================================
    # HISTORICAL DATA
    # ==========================================
    
    def get_historical_candles(
        self, 
        symbol: str, 
        interval: str = "FIVE_MINUTE",
        from_date: str = None,
        to_date: str = None,
        days_back: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLC candles from AngelOne
        """
        try:
            if not self.ensure_api_client():
                logger.error("Cannot fetch data: AngelOne client not initialized.")
                return None
            token = self.get_instrument_token(symbol)
            if not token:
                logger.error(f"Cannot fetch data: No token for {symbol}")
                return None
            
            # Map typical intervals like '5m', '1d' to AngelOne format
            interval_map = {
                "1m": "ONE_MINUTE",
                "5m": "FIVE_MINUTE",
                "15m": "FIFTEEN_MINUTE",
                "30m": "THIRTY_MINUTE",
                "1h": "ONE_HOUR",
                "1d": "ONE_DAY"
            }
            mapped_interval = interval_map.get(interval, interval)
            
            if not from_date or not to_date:
                to_dt = datetime.now()
                from_dt = to_dt - timedelta(days=days_back)
                from_date = from_dt.strftime("%Y-%m-%d 09:15")
                to_date = to_dt.strftime("%Y-%m-%d %H:%M")
            
            historic_param = {
                "exchange": "NSE",
                "symboltoken": token,
                "interval": mapped_interval,
                "fromdate": from_date,
                "todate": to_date
            }
            
            logger.info(f"Fetching {symbol} candles: {interval} from {from_date} to {to_date}")
            
            response = self.smart_api.getCandleData(historic_param)
            
            if not response or response['status'] == False:
                error_msg = response.get('message', 'Unknown error')
                logger.error(f"Historical data fetch failed: {error_msg}")
                return None
            
            candles = response['data']
            
            if not candles or len(candles) == 0:
                logger.warning(f"No candles returned for {symbol}")
                return None
            
            df = pd.DataFrame(
                candles,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"✅ Fetched {len(df)} candles for {symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Exception fetching candles for {symbol}: {str(e)}")
            return None
    
    # ==========================================
    # LIVE QUOTES
    # ==========================================
    
    def get_live_quotes(self, symbols: List[str]) -> Dict:
        """
        Get real-time LTP for multiple symbols
        """
        try:
            quotes = {}
            if not self.ensure_api_client():
                return {}
            
            for symbol in symbols:
                token = self.get_instrument_token(symbol)
                if not token:
                    continue
                
                ltp_data = self.smart_api.ltpData("NSE", symbol, token)
                
                if ltp_data and ltp_data['status']:
                    data = ltp_data['data']
                    quotes[symbol] = {
                        "ltp": float(data['ltp']),
                        "close": float(data.get('close', data['ltp']))
                    }
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error fetching live quotes: {str(e)}")
            return {}
    
    # ==========================================
    # ORDER EXECUTION (Future Enhancement)
    # ==========================================
    
    def place_order(self, order_params: Dict) -> Dict:
        """
        Place order via AngelOne
        """
        logger.warning("Order execution not yet implemented")
        return {"status": "error", "message": "Not implemented"}

_angelone_instance = None

def get_angelone_feed() -> AngelOneFeed:
    """
    Singleton pattern for AngelOne feed
    """
    global _angelone_instance
    if _angelone_instance is None:
        _angelone_instance = AngelOneFeed()
    return _angelone_instance

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    feed = AngelOneFeed()
    
    API_KEY = os.getenv("ANGEL_API_KEY")
    CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
    PIN = os.getenv("ANGEL_PIN")
    TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
    
    if not all([API_KEY, CLIENT_CODE, PIN, TOTP_SECRET]):
        print("❌ Set environment variables: ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PIN, ANGEL_TOTP_SECRET")
        exit(1)
    
    result = feed.login(API_KEY, CLIENT_CODE, PIN, TOTP_SECRET)
    
    if result['status'] == 'success':
        print("✅ Login successful!")
        df = feed.get_historical_candles("RELIANCE", interval="FIVE_MINUTE", days_back=1)
        if df is not None:
            print(f"✅ Fetched {len(df)} candles for RELIANCE")
            print(df.head())
        else:
            print("❌ Failed to fetch historical data")
    else:
        print(f"❌ Login failed: {result['message']}")
