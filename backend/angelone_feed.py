"""
AngelOne SmartAPI Integration Feed.
Acts as the unified data & execution provider for ApexTrade.
Handles authentication, websocket streams, and historical data fetching.
"""

import os
import json
import time
import shutil
import tempfile
import threading
import pyotp
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from SmartApi import SmartConnect
from typing import Optional, Dict, List

from app.core.config import settings
from app.core.logging import configure_json_logging, logger
import db


# Sentinel user ID for background / system tasks (not tied to any real user)
SYSTEM_USER_ID = "__system__"

# Credentials planted by backend/tests (test_broker_sessions.py leaks them into
# the real DB because the login endpoint saves via app.db, which is not mocked).
# A stored session holding any of these must never be restored.
_PLACEHOLDER_SESSION_VALUES = {
    "test_key", "test_code", "test_client", "test_pin", "test_totp",
    "jwt456", "refresh456", "feed456",
    "mock_session", "mock_refresh", "mock_feed",
}


def _session_is_placeholder(session: dict) -> bool:
    return any(
        str(session.get(field) or "") in _PLACEHOLDER_SESSION_VALUES
        for field in ("api_key", "client_code", "pin", "totp_secret",
                      "session_token", "refresh_token", "feed_token")
    )


# Sessions are written in two legacy formats: aware UTC ISO (newer code paths)
# and naive IST wall-clock strings (db._now_ist). Normalize to aware UTC.
_IST = timezone(timedelta(hours=5, minutes=30))


def _parse_session_timestamp(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        try:
            parsed = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_IST)  # legacy _now_ist() values are IST
    return parsed.astimezone(timezone.utc)


def _stabilize_ca_bundle():
    """
    certifi's CA bundle lives inside the virtualenv. When the project (and its
    venv) sit in a OneDrive-synced folder, OneDrive sync can transiently hide
    the file and requests fails with "Could not find a suitable TLS CA
    certificate bundle, invalid path: ...". Copy the bundle once to a stable
    per-user location and point requests at the copy.
    """
    try:
        import certifi
        src = certifi.where()
        if "onedrive" not in src.lower():
            return
        if os.environ.get("REQUESTS_CA_BUNDLE"):
            return
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        dst = Path(base) / "apextrade" / "cacert.pem"
        if dst.exists():
            os.environ["REQUESTS_CA_BUNDLE"] = str(dst)
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        os.environ["REQUESTS_CA_BUNDLE"] = str(dst)
        logger.info(f"CA bundle copied out of OneDrive-synced venv to {dst}")
    except Exception:
        # If the bundle is momentarily locked by OneDrive, fall back to
        # certifi's default resolution rather than failing the import.
        pass


_stabilize_ca_bundle()


class AngelOneFeed:
    """
    Unified wrapper for AngelOne SmartAPI
    Handles: Authentication, Market Data, Historical Data, Order Execution
    """

    LOGIN_COOLDOWN = 30.0  # seconds between full auto-login attempts (3 rps API limit)

    def __init__(self):
        self.smart_api = None
        self.session_token = None
        self.refresh_token = None
        self.feed_token = None
        self.client_code = None
        self.instruments = {}
        self.instruments_file = Path(os.path.join(os.path.dirname(__file__), "angelone_instruments.json"))

        self._instruments_lock = threading.Lock()
        self._login_lock = threading.Lock()
        self._refresh_lock = threading.Lock()  # guards session-refresh retries in get_live_quotes
        self._last_login_attempt = 0.0
        self._paper_order_cache: dict[int, dict] = {}  # prediction_id -> order result
        self._restore_session()

    def _restore_session(self):
        """Restore session from DB on startup, auto-refresh if stale."""
        try:
            saved = db.get_angelone_session() or {}
            if _session_is_placeholder(saved):
                logger.warning(
                    "Stored AngelOne session contains test/placeholder credentials — "
                    "purging it. Log in with real credentials to restore data feeds."
                )
                db.delete_angelone_session()
                return
            if saved.get('session_token'):
                if self.is_session_valid(saved):
                    self.session_token = saved['session_token']
                    self.refresh_token = saved.get('refresh_token')
                    self.feed_token = saved.get('feed_token')
                    self.client_code = saved.get('client_code')
                    # db.get_angelone_session() already decrypts api_key
                    api_key = saved.get('api_key')
                    if api_key:
                        self.smart_api = SmartConnect(api_key=api_key)
                        self.smart_api.setAccessToken(self.session_token)
                    logger.info("✅ Restored AngelOne session from DB")
                else:
                    logger.info("Stored session is stale, attempting auto-login...")
                    self.auto_login()
        except Exception as e:
            logger.warning(f"Session restore skipped: {e}")

    # ==========================================
    # AUTHENTICATION
    # ==========================================

    def login(self, api_key: str, client_code: str, pin: str, totp_code: str = None, totp_secret: str = None) -> Dict:
        """
        Authenticate with AngelOne using TOTP-based login
        """
        try:
            # Initialize SmartConnect
            self.smart_api = SmartConnect(api_key=api_key)
            self.client_code = client_code

            logger.info(f"Attempting AngelOne login for client: {client_code}")

            raw_totp = totp_code or totp_secret or ""
            code_to_send = raw_totp.strip()
            if len(code_to_send) > 6:
                try:
                    import pyotp
                    code_to_send = pyotp.TOTP(code_to_send).now()
                except Exception as pyotp_err:
                    logger.warning(f"pyotp generation fallback failed: {pyotp_err}")

            # Generate session
            session_data = self.smart_api.generateSession(
                clientCode=client_code, password=pin, totp=code_to_send
            )

            if not session_data or not isinstance(session_data, dict) or session_data.get("status") is False:
                error_msg = (
                    session_data.get("message", "Unknown error")
                    if isinstance(session_data, dict)
                    else "Empty response"
                )
                logger.error(f"AngelOne login failed: {error_msg}")
                return {"status": "error", "message": error_msg}

            # Extract tokens
            data = session_data.get("data") or {}
            self.session_token = data.get("jwtToken")
            self.refresh_token = data.get("refreshToken")
            self.feed_token = data.get("feedToken")

            if not self.session_token:
                logger.error("AngelOne login succeeded but no JWT token was returned")
                return {"status": "error", "message": "Login succeeded but no session token was returned"}

            # Set access token for subsequent calls
            self.smart_api.setAccessToken(self.session_token)

            logger.info("✅ AngelOne authentication successful")
            
            # Download instrument master in background to prevent blocking
            self._download_instrument_master(background=True)
            
            return {
                "status": "success",
                "session_token": self.session_token,
                "refresh_token": self.refresh_token,
                "feed_token": self.feed_token,
                "client_code": client_code,
            }

        except Exception as e:
            logger.error(f"AngelOne login exception: {str(e)}")
            return {"status": "error", "message": str(e)}

    def ensure_api_client(self) -> bool:
        """
        Restore API client state if server restarted but session exists in DB
        """
        if self.smart_api and self.session_token:
            return True
        try:
            session = db.get_angelone_session()
            if session and _session_is_placeholder(session):
                logger.warning(
                    "Stored AngelOne session contains test/placeholder credentials — "
                    "purging instead of restoring."
                )
                db.delete_angelone_session()
                return False
            if session and session.get("api_key"):
                api_key = session["api_key"]
                self.smart_api = SmartConnect(api_key=api_key)
                self.client_code = session["client_code"]
                self.session_token = session["session_token"]
                self.refresh_token = session["refresh_token"]
                self.feed_token = session["feed_token"]

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

            if response and response.get("status") is True:
                data = response.get("data") or {}
                new_jwt = data.get("jwtToken")
                if not new_jwt:
                    logger.error("Session refresh returned success but no new JWT token")
                    return False
                self.session_token = new_jwt
                if data.get("refreshToken"):
                    self.refresh_token = data.get("refreshToken")
                if data.get("feedToken"):
                    self.feed_token = data.get("feedToken")

                self.smart_api.setAccessToken(self.session_token)
                self.smart_api.setRefreshToken(self.refresh_token)
                self.smart_api.setFeedToken(self.feed_token)

                # Persist the refreshed credentials back to database
                cached_session = db.get_angelone_session() or {}
                db.save_angelone_session(
                    {
                        "api_key": cached_session.get("api_key", ""),
                        "client_code": self.client_code,
                        "pin": cached_session.get("pin", ""),
                        "totp_secret": cached_session.get("totp_secret", ""),
                        "session_token": self.session_token,
                        "refresh_token": self.refresh_token,
                        "feed_token": self.feed_token,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                logger.info("✅ AngelOne session refreshed and updated in DB")
                return True
            else:
                error_msg = (
                    response.get("message", "Unknown error")
                    if isinstance(response, dict)
                    else "No response"
                )
                logger.error(f"Session refresh failed: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Session refresh exception: {str(e)}")
            return False

    def auto_login(self) -> bool:
        """
        Attempt a full login using saved credentials from the database.
        Guarded so concurrent callers never stampede the rate-limited login API:
        one attempt runs at a time and retries back off for LOGIN_COOLDOWN.
        """
        if not self._login_lock.acquire(blocking=False):
            # Another thread is already logging in: wait for it, then report state
            if self._login_lock.acquire(timeout=15):
                self._login_lock.release()
                return self.session_token is not None
            return False
        try:
            if time.time() - self._last_login_attempt < self.LOGIN_COOLDOWN:
                # A recent attempt exists: report current session state, don't retry
                return self.session_token is not None
            self._last_login_attempt = time.time()
            return self._auto_login_unlocked()
        finally:
            self._login_lock.release()

    def _auto_login_unlocked(self) -> bool:
        """
        Attempt a full login using saved credentials from the database.
        Caller must hold self._login_lock.
        """
        try:

            # Get raw encrypted session data from database
            with db._conn() as c:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
                )
                row = c.execute(
                    "SELECT value FROM app_settings WHERE key='angelone_session'"
                ).fetchone()
                if not row:
                    logger.info(
                        "No stored credentials found in database for auto-login."
                    )
                    return False

                import json

                encrypted_session = json.loads(row["value"])

            # Decrypt sensitive fields using fernet
            if not fernet:
                logger.warning(
                    "Fernet not available, using decrypted values from session (fallback)"
                )
                # Fallback to get_angelone_session if fernet not available
                session = db.get_angelone_session()
                if not session or not all(
                    k in session
                    for k in ("api_key", "client_code", "pin", "totp_secret")
                ):
                    logger.info(
                        "No stored credentials found in database for auto-login."
                    )
                    return False

                api_key = session.get("api_key")
                pin = session.get("pin")
                totp_secret = session.get("totp_secret")
                client_code = session["client_code"]
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

                api_key = decrypt_if_encrypted(encrypted_session.get("api_key"))
                pin = decrypt_if_encrypted(encrypted_session.get("pin"))
                totp_secret = decrypt_if_encrypted(encrypted_session.get("totp_secret"))
                client_code = encrypted_session.get(
                    "client_code"
                )  # client_code is not encrypted

            if not all([api_key, pin, totp_secret, client_code]):
                logger.info("Missing required credentials after decryption.")
                return False

            logger.info(
                "Attempting full auto-login with stored database credentials..."
            )
            import pyotp

            totp_code = pyotp.TOTP(totp_secret).now()

            result = self.login(
                api_key=api_key, client_code=client_code, pin=pin, totp_code=totp_code
            )
            if result.get("status") == "success":
                # Save the new session info back to db
                db.save_angelone_session(
                    {
                        "api_key": api_key,
                        "client_code": client_code,
                        "pin": pin,
                        "totp_secret": totp_secret,
                        "session_token": result["session_token"],
                        "refresh_token": result["refresh_token"],
                        "feed_token": result["feed_token"],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                logger.info(
                    "✅ Full auto-login successful; session credentials updated in DB."
                )
                return True
            else:
                logger.error(f"Full auto-login failed: {result.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Exception during auto-login: {e}")
            return False

    def is_session_valid(self, session_data=None) -> bool:
        """Check if the stored session can still authenticate.

        Angel One SmartAPI JWTs expire at 05:00 IST every day, regardless of
        when they were issued, so a token is only usable until the next 05:00
        IST strictly after it was created. A 24h hard backstop covers clock
        oddities. Legacy rows may carry a naive IST timestamp (db._now_ist)
        or an aware UTC ISO string (newer writes) — both are handled.

        Args:
            session_data: Optional session dict from DB. If provided, uses that data
                         instead of querying DB again. Useful during startup when
                         self.session_token not yet set.
        """
        if session_data is None:
            session_data = db.get_angelone_session() or {}

        updated_at = session_data.get("updated_at")
        session_token = session_data.get("session_token") or self.session_token

        if not updated_at or not session_token:
            return False

        issued = _parse_session_timestamp(updated_at)
        if issued is None:
            return False

        ist = timezone(timedelta(hours=5, minutes=30))
        issued_ist = issued.astimezone(ist)
        expiry_ist = issued_ist.replace(hour=5, minute=0, second=0, microsecond=0)
        if expiry_ist <= issued_ist:
            expiry_ist += timedelta(days=1)

        now = datetime.now(timezone.utc)
        hard_backstop = issued + timedelta(hours=24)
        return now < min(expiry_ist, hard_backstop)

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
            if profile and profile.get("status") is True:
                return True
        except Exception as e:
            logger.warning(f"AngelOne getProfile failed: {e}. Trying refresh...")

        # Try refreshing session using the refresh token
        if self.refresh_token:
            success = self.refresh_session(self.refresh_token)
            if success:
                try:
                    profile = self.smart_api.getProfile(self.refresh_token)
                    if profile and profile.get("status") is True:
                        return True
                except Exception as e:
                    logger.error(f"AngelOne getProfile failed after refresh: {e}")

        # If refresh failed, try full auto_login
        logger.info(
            "Refresh token failed or not present. Attempting full auto_login..."
        )
        if self.auto_login():
            try:
                profile = self.smart_api.getProfile(self.refresh_token)
                return profile and profile.get("status") is True
            except Exception as e:
                logger.error(f"AngelOne getProfile failed after auto_login: {e}")

        return False

    # ==========================================
    # INSTRUMENT MASTER
    # ==========================================
    
    def _download_instrument_master(self, background: bool = False) -> bool:
        """
        Download and cache AngelOne instrument master
        """
        def download_task():
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
                    new_instruments = {
                        inst['symbol']: {
                            'token': inst['token'],
                            'symbol': inst['symbol'],
                            'name': inst['name'],
                            'lotsize': inst['lotsize'],
                            'tick_size': inst['tick_size']
                        }
                        for inst in nse_instruments
                    }

                    with self._instruments_lock:
                        self.instruments = new_instruments
                        # Save to disk safely
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

        if background:
            import threading
            threading.Thread(target=download_task, daemon=True).start()
            return True
        else:
            return download_task()
    
    def get_instrument_token(self, symbol: str) -> Optional[str]:
        """
        Get AngelOne token for a symbol
        """
        if not self.instruments:
            if not self.instruments_file.exists():
                self._download_instrument_master(background=False)
            if self.instruments_file.exists():
                with self._instruments_lock:
                    with open(self.instruments_file, 'r') as f:
                        self.instruments = json.load(f)
        
        # Normalize symbol (remove -EQ suffix or .NS if present)
        clean_symbol = symbol.replace("-EQ", "").replace(".NS", "").upper() + "-EQ"

        if clean_symbol in self.instruments:
            return self.instruments[clean_symbol]["token"]

        # Try raw just in case
        if symbol.upper() in self.instruments:
            return self.instruments[symbol.upper()]["token"]

        # Try without any suffix
        clean_base = symbol.replace("-EQ", "").replace(".NS", "").upper()
        if clean_base in self.instruments:
            return self.instruments[clean_base]["token"]

        # Dynamic search via SmartAPI if available
        if self.ensure_api_client():
            try:
                # Bypass the buggy SDK method that throws KeyError on Invalid Token
                payload = {"exchange": "NSE", "searchscrip": clean_base}
                res = self.smart_api._postRequest("api.search.scrip", payload)

                # Handle session expiry gracefully
                if res and res.get("errorCode") in (
                    "AB2000",
                    "AB1010",
                    "AG001",
                    "AG8001",
                ):
                    logger.warning(
                        f"Session expired during searchScrip for {symbol}. Invalidating token."
                    )
                    self.session_token = None
                    return None

                # 'status' key exists on success, but not on AG8001 error
                if res and res.get("status") is True and res.get("data"):
                    for item in res["data"]:
                        if (
                            item["tradingSymbol"] == clean_base
                            or item["tradingSymbol"] == clean_base + "-EQ"
                        ):
                            # Cache it so we don't look it up again
                            self.instruments[clean_base] = {
                                "token": item["symbolToken"],
                                "symbol": item["tradingSymbol"],
                                "name": item.get("companyName", clean_base),
                                "lotsize": item.get("lotSize", "1"),
                                "tick_size": item.get("tickSize", "0.05"),
                            }
                            logger.info(
                                f"Dynamically discovered and cached token {item['symbolToken']} for {clean_base}"
                            )
                            return item["symbolToken"]
            except Exception as e:
                logger.error(f"searchScrip dynamic lookup failed for {symbol}: {e}")

        logger.warning(
            f"Symbol {symbol} not found in instrument master or dynamic lookup"
        )
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
        days_back: Optional[int] = None,
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
                logger.error(f"Cannot fetch data: No token for {symbol}", extra={"symbol": symbol})
                return None

            # Map typical intervals like '5m', '1d' to AngelOne format
            interval_map = {
                "1m": "ONE_MINUTE",
                "5m": "FIVE_MINUTE",
                "15m": "FIFTEEN_MINUTE",
                "30m": "THIRTY_MINUTE",
                "1h": "ONE_HOUR",
                "1d": "ONE_DAY",
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
                "todate": to_date,
            }

            logger.info(
                f"Fetching {symbol} candles: {interval} from {from_date} to {to_date}",
                extra={"symbol": symbol}
            )

            response = self.smart_api.getCandleData(historic_param)

            if not response or response.get("status") is False:
                error_code = (
                    response.get("errorCode") or response.get("errorcode")
                    if response
                    else ""
                )
                # AB2000 / AB1010 / AG001 / AG8001 are typical session token / auth error codes
                if error_code in ("AB2000", "AB1010", "AG001", "AG8001") or (
                    response and "token" in str(response.get("message", "")).lower()
                ):
                    logger.info("Session token expired/invalid. Trying auto-refresh...")
                    if self.refresh_token and self.refresh_session(self.refresh_token):
                        logger.info(
                            "Token refreshed successfully. Retrying getCandleData..."
                        )
                        response = self.smart_api.getCandleData(historic_param)
                    else:
                        logger.info(
                            "Auto-refresh failed or no refresh token. Trying full auto-login..."
                        )
                        if self.auto_login():
                            logger.info(
                                "Auto-login successful. Retrying getCandleData..."
                            )
                            response = self.smart_api.getCandleData(historic_param)
                        else:
                            self.session_token = None

            if not response or response.get("status") is False:
                error_msg = (
                    response.get("message", "Unknown error")
                    if response
                    else "No response"
                )
                logger.error(f"Historical data fetch failed: {error_msg}")
                return None

            candles = response["data"]

            if not candles or len(candles) == 0:
                logger.warning(f"No candles returned for {symbol}")
                return None

            # Use Capitalized columns as expected by indicators in signals.py & data_mining.py
            df = pd.DataFrame(
                candles, columns=["Date", "Open", "High", "Low", "Close", "Volume"]
            )

            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.info(f"✅ Fetched {len(df)} candles for {symbol}", extra={"symbol": symbol})

            return df

        except Exception as e:
            logger.error(f"Exception fetching candles for {symbol}: {str(e)}", extra={"symbol": symbol})
            return None

    # ==========================================
    # LIVE QUOTES
    # ==========================================

    def _refresh_if_needed(self) -> bool:
        """Try to refresh session if token is invalid. Returns True if refreshed."""
        if not self.refresh_token:
            return False
        success = self.refresh_session(self.refresh_token)
        return success

    def _try_get_market_data(self, batch_tokens: List[str]) -> Optional[dict]:
        """Attempt a single getMarketData call, refresh session on auth error."""
        try:
            response = self.smart_api.getMarketData("FULL", {"NSE": batch_tokens})
            if not response or response.get("status") is False:
                error_code = (
                    response.get("errorCode") or response.get("errorcode")
                    if response
                    else ""
                )
                is_auth_error = error_code in (
                    "AB2000", "AB1010", "AG001", "AG8001"
                ) or (
                    response and "token" in str(response.get("message", "")).lower()
                )
                if is_auth_error and self._refresh_if_needed():
                    response = self.smart_api.getMarketData("FULL", {"NSE": batch_tokens})
            return response
        except Exception:
            return None

    def get_live_quotes(self, symbols: List[str]) -> Dict:
        """
        Get real-time quotes for multiple symbols using AngelOne's batch getMarketData.
        Returns empty dict on any failure — never raises.
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
            batches = [
                tokens[i : i + batch_size] for i in range(0, len(tokens), batch_size)
            ]

            from concurrent.futures import ThreadPoolExecutor, as_completed

            def fetch_batch_sync(batch_tokens):
                response = self._try_get_market_data(batch_tokens)
                return response

            responses = []
            with ThreadPoolExecutor(max_workers=min(10, len(batches) or 1)) as executor:
                futures = [
                    executor.submit(fetch_batch_sync, batch) for batch in batches
                ]
                for future in as_completed(futures):
                    try:
                        responses.append(future.result())
                    except Exception as exc:
                        logger.error(f"Error fetching batch: {exc}")
                        responses.append(None)

            for response in responses:
                if not response or response.get("status") is not True or not response.get("data"):
                    continue

                fetched = response["data"].get("fetched") or []
                for item in fetched:
                    token = item.get("symbolToken")
                    orig_symbol = token_to_symbol.get(token)
                    if not orig_symbol:
                        continue
                    price = float(item.get("ltp") or item.get("lastPrice") or 0.0)
                    open_p = float(item.get("open") or price)
                    high = float(item.get("high") or price)
                    low = float(item.get("low") or price)
                    prev_close = float(item.get("close") or price)
                    volume = int(item.get("tradeVolume") or item.get("volume") or 0)

                    net_change = float(item.get("netChange") or (price - prev_close))
                    percent_change = float(
                        item.get("percentChange")
                        or ((net_change / prev_close * 100) if prev_close else 0.0)
                    )

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

    def _compute_slippage_pct(self, symbol: str, entry_price: float, stop_loss: float) -> float:
        """
        Compute dynamic slippage percentage based on stop distance.
        
        - If entry <= 0 or stop <= 0: return 0.05 (minimum floor)
        - Stop distance % = abs(entry - stop) / entry * 100
        - Slippage % = stop_distance_pct * 0.15, capped at 1.0, minimum floor 0.05
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0.05
        
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
        slippage = stop_distance_pct * 0.15
        
        # Cap at 1.0%, floor at 0.05%
        return max(0.05, min(1.0, slippage))

    def place_order(self, params: dict, user_id: str = None) -> dict:
        """
        Place order - routes to paper execution when mode != "live" or LIVE_TRADING_ARMED is False.
        
        Paper orderid format: f"PAPER-{prediction_id}-{action}-{symbol}"
        Live orderid format: f"LIVE-{prediction_id}-{action}-{symbol}"
        Return shape: {"status": True, "message": "SUCCESS", "data": {"orderid": orderid, "slippage_pct": slippage}}
        Idempotency: Cache orders by prediction_id in an in-memory dictionary.
        """
        prediction_id = params.get("prediction_id")
        action = params.get("action", "BUY") or "BUY"
        symbol = str(params.get("symbol") or "UNKNOWN").replace(".NS", "").replace("-EQ", "")
        entry_price = float(params.get("entry_price") or 0.0)
        stop_loss = float(params.get("stop_loss") or 0.0)
        
        # Idempotency: check cache
        if prediction_id is not None and prediction_id in self._paper_order_cache:
            return self._paper_order_cache[prediction_id]
        
        # Compute slippage
        slippage = self._compute_slippage_pct(symbol, entry_price, stop_loss)
        
        # Determine if paper mode
        is_live = getattr(settings, "trading_mode", "paper") == "live" and getattr(settings, "live_trading_armed", False)
        
        prefix = "LIVE" if is_live else "PAPER"
        orderid = f"{prefix}-{prediction_id}-{action}-{symbol}" if prediction_id else f"{prefix}-{id(params)}"
        
        result = {
            "status": True,
            "message": "SUCCESS",
            "data": {
                "orderid": orderid,
                "slippage_pct": slippage
            }
        }
        
        # Cache for idempotency (only for paper mode)
        if prediction_id is not None and not is_live:
            self._paper_order_cache[prediction_id] = result
        
        return result


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
    configure_json_logging()

    feed = AngelOneFeed()

    API_KEY = os.getenv("ANGEL_API_KEY")
    # backend/.env names it ANGEL_CLIENT_ID; accept both spellings
    CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE") or os.getenv("ANGEL_CLIENT_ID")
    PIN = os.getenv("ANGEL_PIN")
    TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

    if not all([API_KEY, CLIENT_CODE, PIN, TOTP_SECRET]):
        logger.error(
            "❌ Set environment variables: ANGEL_API_KEY, ANGEL_CLIENT_CODE (or ANGEL_CLIENT_ID), ANGEL_PIN, ANGEL_TOTP_SECRET"
        )
        exit(1)

    import pyotp

    totp_code = pyotp.TOTP(TOTP_SECRET).now()
    result = feed.login(API_KEY, CLIENT_CODE, PIN, totp_code)

    if result["status"] == "success":
        logger.info("✅ Login successful!")
        df = feed.get_historical_candles(
            "RELIANCE", interval="FIVE_MINUTE", days_back=1
        )
        if df is not None:
            logger.info(f"✅ Fetched {len(df)} candles for RELIANCE", extra={"symbol": "RELIANCE"})
            logger.info(df.head())
        else:
            logger.error("❌ Failed to fetch historical data")
    else:
        logger.error(f"❌ Login failed: {result['message']}")
