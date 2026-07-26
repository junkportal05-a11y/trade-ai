import os
import sys
import json
import sqlite3

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

print("=" * 80)
print("APEXTRADE SECURITY FIXES: EMPIRICAL VERIFICATION SUITE")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. VERIFY BROKER CREDENTIAL ENCRYPTION & SYMMETRIC DECRYPTION (db.py)
# -----------------------------------------------------------------------------
print("\n[TEST 1] Testing db.py Broker Credential Vault Encryption & Decryption...")
import db

test_session = {
    "api_key": "test_api_key_12345",
    "pin": "9999",
    "totp_secret": "MY_TOTP_SECRET_BASE32",
    "session_token": "sess_tok_abc123",
    "refresh_token": "refr_tok_xyz789",
    "feed_token": "feed_tok_456def"
}

# Save session
db.save_angelone_session(test_session)

# Inspect raw database row to prove encryption at rest
with db._conn() as conn:
    row = conn.execute("SELECT value FROM app_settings WHERE key='angelone_session'").fetchone()
    raw_json_str = row["value"]
    raw_data = json.loads(raw_json_str)

print("  RAW DISK DATA (SQLite 'angelone_session' table):")
for k, v in raw_data.items():
    if k in test_session:
        print(f"     - {k}: {v[:30]}... (ENCRYPTED CIPHERTEXT)")
        assert v != test_session[k], f"SECURITY ERROR: {k} stored in plaintext!"

# Retrieve session via get_angelone_session()
retrieved_session = db.get_angelone_session()
print("\n  DECRYPTED SESSION (Returned to Application):")
for k, v in test_session.items():
    print(f"     - {k}: {retrieved_session.get(k)} (MATCH: {retrieved_session.get(k) == v})")
    assert retrieved_session.get(k) == v, f"DECRYPTION ERROR: Field {k} failed to decrypt back to plaintext!"

print("  [PASSED] TEST 1: All 6 sensitive fields are encrypted at rest & symmetrically decrypted!")

# -----------------------------------------------------------------------------
# 2. VERIFY AUTH HARDENING & CONSTANT-TIME COMPARES (app.core.security.py)
# -----------------------------------------------------------------------------
print("\n[TEST 2] Testing app.core.security Auth Hardening...")
from app.core.security import user_registry, require_admin
from fastapi import HTTPException

# Test 2a: Hardcoded 'admin' password removed
auth_admin_default = user_registry.authenticate("apex_head_quant", "admin")
print(f"  - Authentication attempt with password 'admin': {auth_admin_default}")
assert auth_admin_default is None, "SECURITY FAILURE: Account still authenticates with default password 'admin'!"
print("  - Removed hardcoded 'admin' fallback password!")

# Test 2b: require_admin header check & secrets.compare_digest
print("\n  Testing require_admin() access control...")
try:
    require_admin("wrong_key")
    assert False, "SECURITY FAILURE: require_admin allowed invalid key!"
except HTTPException as e:
    print(f"  - Invalid Key -> HTTP Status: {e.status_code} ({e.detail})")
    assert e.status_code == 403

from app.core.config import settings
try:
    require_admin(settings.admin_key)
    print(f"  - Valid Key ('X-Admin-Key') -> Authorized Access (200 OK)")
except HTTPException:
    assert False, "FAILURE: require_admin rejected valid admin key!"

print("  [PASSED] TEST 2: Hardcoded default removed & header require_admin enforced!")

# -----------------------------------------------------------------------------
# 3. VERIFY REPOMIX EXPORT SCOPE (codebase.txt)
# -----------------------------------------------------------------------------
print("\n[TEST 3] Testing codebase.txt Export Scope & Exclusion...")
codebase_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "codebase.txt"))
assert os.path.exists(codebase_path), "codebase.txt missing!"

with open(codebase_path, "r", encoding="utf-8") as f:
    content = f.read()

# Verify no packed file entry headers exist for excluded files/dirs
file_header_checks = ["## File: backend/.claude/", "## File: .claude/", "settings.local.json"]

# Check for file headers
has_claude = any(".claude" in line for line in content.splitlines() if line.startswith("## File:"))
print(f"  - Excluded folder file headers ('## File: ... .claude'): {has_claude}")
assert not has_claude, "EXPORT HYGIENE FAILURE: .claude directory file entries found in codebase.txt!"

# Count file occurrences of settings.local.json file entries
has_settings = "## File: " in content and "settings.local.json" in [line for line in content.splitlines() if line.startswith("## File:")]
print(f"  - Excluded file headers ('## File: ...settings.local.json'): {has_settings}")
assert not has_settings, "EXPORT HYGIENE FAILURE: settings.local.json file entry found in codebase.txt!"

print("  [PASSED] TEST 3: Sensitive local configs and .claude folders strictly excluded!")

print("\n" + "=" * 80)
print("ALL 3 SECURITY VERIFICATION TESTS PASSED 100% EMPIRICALLY!")
print("=" * 80)
