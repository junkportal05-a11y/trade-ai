"""
One-shot cleanup for the AG8001 "Invalid Token" incident.

The backend test suite leaked placeholder AngelOne credentials
(test_key / test_code / test_pin / test_totp / jwt456 / refresh456 / feed456)
into the real database (app_settings.key='angelone_session'), because the
/api/angelone/login endpoint saves via app.api.v1.broker's own import of
app.db, which the tests' mock_db fixture did not patch. On startup the app
restored that fake session and every Angel One API call failed with AG8001.

This script deletes the stored row ONLY if it contains the known placeholder
values. Run with the project venv:

    .venv/Scripts/python.exe scripts/purge_placeholder_angelone_session.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import db  # backend/db.py — loads backend/.env and the same engine the app uses

PLACEHOLDERS = {
    "test_key", "test_code", "test_client", "test_pin", "test_totp",
    "jwt456", "refresh456", "feed456",
    "mock_session", "mock_refresh", "mock_feed",
}


def main() -> int:
    saved = db.get_angelone_session() or {}
    if not saved:
        print("No stored AngelOne session found — nothing to purge.")
        return 0

    hit = sorted({k for k, v in saved.items() if str(v or "") in PLACEHOLDERS})
    if not hit:
        print("Stored session does not contain placeholder values; leaving it in place.")
        return 0

    if db.delete_angelone_session():
        print(f"Purged poisoned angelone_session row (placeholder fields: {', '.join(hit)}).")
        print("Re-login with real Angel One credentials to restore data feeds.")
        return 0
    print("ERROR: failed to delete the row — check logs.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
