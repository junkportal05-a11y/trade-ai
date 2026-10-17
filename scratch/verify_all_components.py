"""
End-to-End Component Verification Suite for ApexTrade AI
"""
import os
import sys
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if os.path.abspath(os.path.join(backend_dir, "..")) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(backend_dir, "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestComponentVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Log in and acquire master session token."""
        res = client.post("/api/login", json={"username": "code", "password": "ApexSecurePass2026!"})
        assert res.status_code == 200, "Login failed"
        data = res.json()
        cls.token = data["token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_api_login_with_credentials(self):
        """Verify /api/login authenticates and returns a valid session token."""
        res = client.post("/api/login", json={"username": "code", "password": "ApexSecurePass2026!"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("token", data)
        self.assertIn("username", data)
        self.assertEqual(data["username"], "apex_head_quant")
        self.assertEqual(data["clearance"], "LEVEL_4_ROOT")

    def test_02_api_scan_signal_generation(self):
        """Verify /api/scan executes scanner pipeline and returns signals."""
        res = client.post("/api/scan", headers=self.headers, json={
            "symbols": ["RELIANCE.NS", "TCS.NS"],
            "interval": "15m",
            "trading_style": "Intraday Momentum",
            "capital": 100000.0,
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("signals", data)
        self.assertIn("scan_time", data)
        self.assertIsInstance(data["signals"], list)

    def test_03_manual_trade_execution_path(self):
        """Verify manual prediction/trade creation in trade journal/prediction history."""
        pred_payload = {
            "symbol": "RELIANCE.NS",
            "prediction_type": "UP",
            "entry_price": 2450.0,
            "target_price": 2520.0,
            "stop_loss": 2410.0,
            "confidence_score": 85,
            "rsi": 48.5,
            "macd": 1.25,
            "adx": 24.1,
        }
        res = client.post("/api/predictions", headers=self.headers, json=pred_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "created")

    def test_04_automatic_bot_execution_path(self):
        """Verify autonomous bot start/status endpoint."""
        res = client.get("/api/bot/status", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("state", data)
        self.assertIn("today_pnl", data)

if __name__ == "__main__":
    print("=" * 70)
    print("VERIFYING ALL APEXTRADE COMPONENTS & EXECUTION PATHS")
    print("=" * 70)
    unittest.main()
