import os
import sys
import json
import subprocess

print("=" * 80)
print("RESTART PERSISTENCE TEST: BROKER CREDENTIAL VAULT")
print("=" * 80)

# Environment variables representing pinned persistent Space secrets
PINNED_ENV = os.environ.copy()
PINNED_ENV["JWT_SECRET"] = "pinned_jwt_secret_key_fixed_token_32chars"
PINNED_ENV["FERNET_KEYS"] = '["8mZ9u-L6T7W89012345678901234567890123456789="]'
PINNED_ENV["ADMIN_KEY"] = "pinned_admin_secret_key_9999"

# Script to run in Process 1 (Writer)
writer_code = """
import sys, os
sys.path.insert(0, os.path.abspath("backend"))
import db

test_session = {
    "api_key": "angel_api_key_persistent",
    "pin": "1234",
    "totp_secret": "TOTP_SECRET_PERSISTENT",
    "session_token": "sess_persistent_token_123",
    "refresh_token": "refr_persistent_token_456",
    "feed_token": "feed_persistent_token_789"
}

db.save_angelone_session(test_session)
print("PROCESS 1: Session saved with Fernet encryption.")
"""

# Script to run in Process 2 (Reader after restart)
reader_code = """
import sys, os
sys.path.insert(0, os.path.abspath("backend"))
import db

retrieved = db.get_angelone_session()
print("PROCESS 2 (POST-RESTART): Retrieved session:")
print("  - session_token:", retrieved.get("session_token"))
print("  - refresh_token:", retrieved.get("refresh_token"))
print("  - feed_token:", retrieved.get("feed_token"))

assert retrieved.get("session_token") == "sess_persistent_token_123", "Session token mismatch!"
assert retrieved.get("refresh_token") == "refr_persistent_token_456", "Refresh token mismatch!"
assert retrieved.get("feed_token") == "feed_persistent_token_789", "Feed token mismatch!"
print("PROCESS 2 SUCCESS: All credentials decrypted successfully after process restart!")
"""

# Execute Process 1
print("\n[STEP 1] Running Process 1 (Simulating server pre-restart save)...")
p1 = subprocess.run([sys.executable, "-c", writer_code], env=PINNED_ENV, capture_output=True, text=True)
print(p1.stdout)
assert p1.returncode == 0, f"Process 1 failed: {p1.stderr}"

# Execute Process 2 (New isolated process)
print("[STEP 2] Running Process 2 (Simulating container restart with pinned secrets)...")
p2 = subprocess.run([sys.executable, "-c", reader_code], env=PINNED_ENV, capture_output=True, text=True)
print(p2.stdout)
assert p2.returncode == 0, f"Process 2 failed: {p2.stderr}"

print("=" * 80)
print("SUCCESS: RESTART PERSISTENCE VERIFIED ACROSS PROCESS BOUNDARY!")
print("=" * 80)
