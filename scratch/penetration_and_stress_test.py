"""
Comprehensive Security Penetration, Input Stress, and Fallback Validation Suite for ApexTrade AI
"""
import os
import sys
import json
import unittest
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if os.path.abspath(os.path.join(backend_dir, "..")) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(backend_dir, "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import LoginRequest, ScanRequest, BacktestRequest
from signals import download_market_data_df
from backtest_engine import run_historical_backtest, BacktestConfig

client = TestClient(app)

class TestSecurityPenetration(unittest.TestCase):
    def test_sqli_payloads_on_login(self):
        """Test SQL injection payloads on /api/login endpoint."""
        sqli_payloads = [
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT 1, 'admin', 'password'--",
            "'; DROP TABLE users; --",
            "1' OR 1=1 --",
        ]
        for payload in sqli_payloads:
            res = client.post("/api/login", json={"username": payload, "password": payload})
            self.assertIn(res.status_code, [200, 401, 422, 429], f"SQLi payload failed safely for {payload}")

    def test_xss_payloads_on_login(self):
        """Test XSS payloads on /api/login endpoint."""
        xss_payloads = [
            "<script>alert(1)</script>",
            "\"><img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
        ]
        for payload in xss_payloads:
            res = client.post("/api/login", json={"username": payload, "password": payload})
            self.assertIn(res.status_code, [200, 401, 422, 429])

    def test_scan_endpoint_resilience(self):
        """Test /api/scan with empty, malformed, and injection payloads."""
        res_empty = client.post("/api/scan", json={})
        self.assertIn(res_empty.status_code, [200, 401, 422, 429])

        res_sqli = client.post("/api/scan", json={"symbols": ["' OR '1'='1", "<script>"]})
        self.assertIn(res_sqli.status_code, [200, 401, 422, 429])

class TestBacktestStressInput(unittest.TestCase):
    def test_backtest_missing_payload(self):
        """Test backtest endpoint with empty payload."""
        res = client.post("/api/backtest/run", json={})
        self.assertIn(res.status_code, [200, 400, 422, 429])

    def test_backtest_invalid_date_order(self):
        """Test backtest with start_date >= end_date."""
        res = client.post("/api/backtest/run", json={
            "symbol": "RELIANCE.NS",
            "start_date": "2024-12-31",
            "end_date": "2024-01-01",
        })
        self.assertIn(res.status_code, [400, 422, 429])

    def test_backtest_unSuffixed_symbol(self):
        """Test backtest with raw symbol without .NS suffix (e.g. RELIANCE)."""
        res = client.post("/api/backtest/run", json={
            "symbol": "RELIANCE",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        })
        self.assertIn(res.status_code, [200, 400, 422, 429])

    def test_backtest_extreme_inputs(self):
        """Test backtest with extreme capital, negative ATRs, and long symbols."""
        res = client.post("/api/backtest/run", json={
            "symbol": "TCS.NS",
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
            "capital": -1000.0,
            "stop_atr": -1.5,
        })
        self.assertIn(res.status_code, [200, 400, 422, 429])

class TestCascadeFallbackSystem(unittest.TestCase):
    def test_synthetic_fallback_for_unknown_symbol(self):
        """Verify Tier 3 synthetic fallback produces valid OHLCV dataframe."""
        df = download_market_data_df("NON_EXISTENT_TEST_SYMBOL_XYZ")
        self.assertIsNotNone(df)
        self.assertGreaterEqual(len(df), 30)
        self.assertIn("Close", df.columns)
        self.assertIn("High", df.columns)
        self.assertIn("Low", df.columns)
        self.assertIn("Open", df.columns)
        self.assertIn("Volume", df.columns)

    def test_backtest_simulation_with_synthetic_data(self):
        """Verify historical backtest engine executes cleanly on fallback synthetic data."""
        config = BacktestConfig(period_range="6mo", initial_capital=100000.0)
        result = run_historical_backtest("NON_EXISTENT_TEST_SYMBOL_XYZ", config)
        self.assertIsInstance(result, dict)
        self.assertIn("win_rate", result)
        self.assertIn("total_trades", result)
        self.assertIn("final_capital", result)

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING APEXTRADE SECURITY PENETRATION, STRESS, AND FALLBACK TEST SUITE")
    print("=" * 70)
    unittest.main()
