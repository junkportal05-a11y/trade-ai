"""
AngelOne SmartAPI Integration Feed.
Acts as the unified data & execution provider for ApexTrade.
Handles authentication, websocket streams, and historical data fetching.
"""

import os
import json
import logging
import pyotp
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from SmartApi import SmartConnect
from typing import Optional, Dict, List
from cryptography.fernet import Fernet

FERNET_KEY = os.getenv("FERNET_KEY")
if FERNET_KEY:
    fernet = Fernet(FERNET_KEY.encode())
else:
    fernet = None

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
    
    def login(self, api_key: str, client_code: str, pin: str, totp_code: str) -> Dict:
        """
        Authenticate with AngelOne using TOTP-based login
        """
        try:
            # Initialize SmartConnect
            self.smart_api = SmartConnect(api_key=api_key)
            self.client_code = client_code

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
                api_key = session['api_key']
                self.smart_api = SmartConnect(api_key=api_key)
                self.client_code = session['client_code']
                self.session_token = session['session_token']
                self.refresh_token = session['refresh_token']
                self.feed_token = session['feed_token']
                
                # Re-inject all tokens on the SmartConnect instance
                self.smart_api.setAccessToken(self.session_token)
                self.smart_api.setRefreshToken(self.refresh_token)
                self.smart_api.setFeedToken(self.feed_token)
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
            
            if response and response.get('status') == True:
                data = response.get('data') or {}
                self.session_token = data.get('jwtToken')
                if data.get('refreshToken'):
                    self.refresh_token = data.get('refreshToken')
                if data.get('feedToken'):
                    self.feed_token = data.get('feedToken')
                
                self.smart_api.setAccessToken(self.session_token)
                self.smart_api.setRefreshToken(self.refresh_token)
                self.smart_api.setFeedToken(self.feed_token)
                
                # Persist the refreshed credentials back to database
                import db
                cached_session = db.get_angelone_session() or {}
                db.save_angelone_session({
                    "api_key": cached_session.get('api_key', ''),
                    "client_code": self.client_code,
                    "pin": cached_session.get('pin', ''),
                    "totp_secret": cached_session.get('totp_secret', ''),
                    "session_token": self.session_token,
                    "refresh_token": self.refresh_token,
                    "feed_token": self.feed_token,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                
                logger.info("✅ AngelOne session refreshed and updated in DB")
                return True
            else:
                logger.error(f"Session refresh failed: {response.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Session refresh exception: {str(e)}")
            return False

    def auto_login(self) -> bool:
        """
        Attempt a full login using saved credentials from the database.
        """
        try:
            import db
            # Get raw encrypted session data from database
            with db._conn() as c:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
                )
                row = c.execute(
                    "SELECT value FROM app_settings WHERE key='angelone_session'"
                ).fetchone()
                if not row:
                    logger.info("No stored credentials found in database for auto-login.")
                    return False

                import json
                encrypted_session = json.loads(row["value"])

            # Decrypt sensitive fields using fernet
            if not fernet:
                logger.warning("Fernet not available, using decrypted values from session (fallback)")
                # Fallback to get_angelone_session if fernet not available
                session = db.get_angelone_session()
                if not session or not all(k in session for k in ('api_key', 'client_code', 'pin', 'totp_secret')):
                    logger.info("No stored credentials found in database for auto-login.")
                    return False

                api_key = session.get('api_key')
                pin = session.get('pin')
                totp_secret = session.get('totp_secret')
                client_code = session['client_code']
            else:
                # Decrypt the fields explicitly
                def decrypt_if_encrypted(value):
                    if value is None:
                        return None
                    try:
                        return fernet.decrypt(value.encode()).decode()
                    except Exception:
                        # If decryption fails, assume it's already decrypted
                        return value

                api_key = decrypt_if_encrypted(encrypted_session.get('api_key'))
                pin = decrypt_if_encrypted(encrypted_session.get('pin'))
                totp_secret = decrypt_if_encrypted(encrypted_session.get('totp_secret'))
                client_code = encrypted_session.get('client_code')  # client_code is not encrypted

            if not all([api_key, pin, totp_secret, client_code]):
                logger.info("Missing required credentials after decryption.")
                return False

            logger.info("Attempting full auto-login with stored database credentials...")
            import pyotp
            totp_code = pyotp.TOTP(totp_secret).now()

            result = self.login(
                api_key=api_key,
                client_code=client_code,
                pin=pin,
                totp_code=totp_code
            )
            if result.get("status") == "success":
                # Save the new session info back to db
                db.save_angelone_session({
                    "api_key": api_key,
                    "client_code": client_code,
                    "pin": pin,
                    "totp_secret": totp_secret,
                    "session_token": result["session_token"],
                    "refresh_token": result["refresh_token"],
                    "feed_token": result["feed_token"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                logger.info("✅ Full auto-login successful; session credentials updated in DB.")
                return True
            else:
                logger.error(f"Full auto-login failed: {result.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Exception during auto-login: {e}")
            return False

    def is_session_valid(self) -> bool:
        import db
        saved = db.get_angelone_session() or {}
        updated_at = saved.get('updated_at')
        if not updated_at or not self.session_token:
            return False
        from datetime import datetime, timezone
        age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).total_seconds() / 3600
        return age_hours < 23

    def is_authorized(self, force_check: bool = False) -> bool:
        """
        Check if current session is valid.
        If force_check is True, makes a network call to verify with the server.
        Otherwise, returns True if the session token is loaded in memory.
        """
        if not self.ensure_api_client():
            if not self.auto_login():
                return False
        
        if not force_check:
            # Fast in-memory check to prevent hitting AngelOne rate limits (3 rps)
            return self.session_token is not None
        
        try:
            profile = self.smart_api.getProfile(self.refresh_token)
            if profile and profile.get('status') == True:
                return True
        except Exception as e:
            logger.warning(f"AngelOne getProfile failed: {e}. Trying refresh...")
            
        # Try refreshing session using the refresh token
        if self.refresh_token:
            success = self.refresh_session(self.refresh_token)
            if success:
                try:
                    profile = self.smart_api.getProfile(self.refresh_token)
                    if profile and profile.get('status') == True:
                        return True
                except Exception as e:
                    logger.error(f"AngelOne getProfile failed after refresh: {e}")
                    
        # If refresh failed, try full auto_login
        logger.info("Refresh token failed or not present. Attempting full auto_login...")
        if self.auto_login():
            try:
                profile = self.smart_api.getProfile(self.refresh_token)
                return profile and profile.get('status') == True
            except Exception as e:
                logger.error(f"AngelOne getProfile failed after auto_login: {e}")
                
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
             
        # Dynamic search via SmartAPI if available
        if self.ensure_api_client():
            try:
                # Bypass the buggy SDK method that throws KeyError on Invalid Token
                payload = {"exchange": "NSE", "searchscrip": clean_base}
                res = self.smart_api._postRequest("api.search.scrip", payload)
                
                # Handle session expiry gracefully
                if res and res.get('errorCode') in ('AB2000', 'AB1010', 'AG001', 'AG8001'):
                    logger.warning(f"Session expired during searchScrip for {symbol}. Invalidating token.")
                    self.session_token = None
                    return None
                
                # 'status' key exists on success, but not on AG8001 error
                if res and res.get('status') is True and res.get('data'):
                    for item in res['data']:
                        if item['tradingSymbol'] == clean_base or item['tradingSymbol'] == clean_base + "-EQ":
                            # Cache it so we don't look it up again
                            self.instruments[clean_base] = {
                                'token': item['symbolToken'],
                                'symbol': item['tradingSymbol'],
                                'name': item.get('companyName', clean_base),
                                'lotsize': item.get('lotSize', '1'),
                                'tick_size': item.get('tickSize', '0.05')
                            }
                            logger.info(f"Dynamically discovered and cached token {item['symbolToken']} for {clean_base}")
                            return item['symbolToken']
            except Exception as e:
                logger.error(f"searchScrip dynamic lookup failed for {symbol}: {e}")
        
        logger.warning(f"Symbol {symbol} not found in instrument master or dynamic lookup")
        return None
    
    # ==========================================
    # HISTORICAL DATA
    # ==========================================
    
    def get_historical_candles(
        self, 
        symbol: str, 
        period_or_range: str = "5d",
        interval: str = "FIVE_MINUTE",
        from_date: str = None,
        to_date: str = None,
        days_back: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for a specific symbol.
        Supports standard feed signatures.
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
            
            if days_back is None:
                p = str(period_or_range).lower()
                if p == "1d":
                    days_back = 2
                elif p == "5d":
                    days_back = 7
                elif p == "60d":
                    days_back = 90
                elif p == "1mo":
                    days_back = 30
                elif p == "3mo":
                    days_back = 90
                elif p == "6mo":
                    days_back = 180
                elif p == "1y":
                    days_back = 365
                elif p == "2y":
                    days_back = 365 * 2
                elif p == "5y":
                    days_back = 365 * 5
                elif p == "max":
                    days_back = 365 * 10
                else:
                    if p.endswith("d"):
                        try:
                            days_back = int(p[:-1]) + 2
                        except:
                            days_back = 7
                    else:
                        days_back = 7

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
            
            if not response or response.get('status') == False:
                error_code = response.get('errorCode') or response.get('errorcode') if response else ''
                # AB2000 / AB1010 / AG001 / AG8001 are typical session token / auth error codes
                if error_code in ('AB2000', 'AB1010', 'AG001', 'AG8001') or (response and 'token' in str(response.get('message', '')).lower()):
                    logger.info("Session token expired/invalid. Trying auto-refresh...")
                    if self.refresh_token and self.refresh_session(self.refresh_token):
                        logger.info("Token refreshed successfully. Retrying getCandleData...")
                        response = self.smart_api.getCandleData(historic_param)
                    else:
                        logger.info("Auto-refresh failed or no refresh token. Trying full auto-login...")
                        if self.auto_login():
                            logger.info("Auto-login successful. Retrying getCandleData...")
                            response = self.smart_api.getCandleData(historic_param)
                        else:
                            self.session_token = None
            
            if not response or response.get('status') == False:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"Historical data fetch failed: {error_msg}")
                return None
            
            candles = response['data']
            
            if not candles or len(candles) == 0:
                logger.warning(f"No candles returned for {symbol}")
                return None
            
            # Use Capitalized columns as expected by indicators in signals.py & data_mining.py
            df = pd.DataFrame(
                candles,
                columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            )
            
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            
            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            
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
        Get real-time quotes for multiple symbols using AngelOne's batch getMarketData
        """
        try:
            quotes = {}
            if not self.ensure_api_client():
                return {}
            
            # Group tokens by exchange (NSE only)
            tokens = []
            token_to_symbol = {}
            for symbol in symbols:
                clean_sym = symbol.replace("-EQ", "").replace(".NS", "").upper() + "-EQ"
                token = self.get_instrument_token(clean_sym)
                if token:
                    tokens.append(token)
                    token_to_symbol[token] = symbol  # map token back to requested symbol format
            
            if not tokens:
                return {}
            
            # Call getMarketData in batches of 50 to respect API limitations
            batch_size = 50
            for i in range(0, len(tokens), batch_size):
                batch_tokens = tokens[i:i+batch_size]
                response = self.smart_api.getMarketData('FULL', {'NSE': batch_tokens})
                
                if not response or response.get('status') == False:
                    error_code = response.get('errorCode') or response.get('errorcode') if response else ''
                    if error_code in ('AB2000', 'AB1010', 'AG001', 'AG8001') or (response and 'token' in str(response.get('message', '')).lower()):
                        logger.info("Session token expired/invalid. Trying auto-refresh...")
                        if self.refresh_token and self.refresh_session(self.refresh_token):
                            logger.info("Token refreshed successfully. Retrying getMarketData...")
                            response = self.smart_api.getMarketData('FULL', {'NSE': batch_tokens})
                        else:
                            logger.info("Auto-refresh failed or no refresh token. Trying full auto-login...")
                            if self.auto_login():
                                logger.info("Auto-login successful. Retrying getMarketData...")
                                response = self.smart_api.getMarketData('FULL', {'NSE': batch_tokens})
                            else:
                                self.session_token = None
                
                if response and response.get('status') and response.get('data'):
                    fetched = response['data'].get('fetched') or []
                    for item in fetched:
                        token = item.get('symbolToken')
                        orig_symbol = token_to_symbol.get(token)
                        if orig_symbol:
                            price = float(item.get('ltp') or item.get('lastPrice') or 0.0)
                            open_p = float(item.get('open') or price)
                            high = float(item.get('high') or price)
                            low = float(item.get('low') or price)
                            prev_close = float(item.get('close') or price)
                            volume = int(item.get('tradeVolume') or item.get('volume') or 0)
                            
                            net_change = float(item.get('netChange') or (price - prev_close))
                            percent_change = float(item.get('percentChange') or ((net_change / prev_close * 100) if prev_close else 0.0))
                            
                            quotes[orig_symbol] = {
                                "symbol": orig_symbol,
                                "name": orig_symbol,
                                "price": round(price, 2),
                                "change": round(net_change, 2),
                                "change_pct": round(percent_change, 2),
                                "volume": volume,
                                "open": round(open_p, 2),
                                "high": round(high, 2),
                                "low": round(low, 2),
                                "prev_close": round(prev_close, 2),
                                "source": "angelone",
                                "sector": "NSE Stock",
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

    import pyotp
    totp_code = pyotp.TOTP(TOTP_SECRET).now()
    result = feed.login(API_KEY, CLIENT_CODE, PIN, totp_code)
    
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
