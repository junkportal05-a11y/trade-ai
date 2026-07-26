import os
import sys
import subprocess

print("=" * 80)
print("TESTING UNPINNED KEY FAILURE DEMONSTRATION")
print("=" * 80)

# Unpinned environment (no FERNET_KEYS set)
UNPINNED_ENV = {k: v for k, v in os.environ.items() if k not in ("FERNET_KEYS", "FERNET_KEY", "JWT_SECRET")}

# Process A writes credentials with random generated key A
process_a_code = """
import sys, os
sys.path.insert(0, os.path.abspath("backend"))
import db

test_session = {
    "api_key": "api_key_unpinned",
    "session_token": "token_unpinned_process_a"
}
db.save_angelone_session(test_session)
print("Process A saved session with auto-generated random Key A.")
"""

# Process B starts in fresh container with UNPINNED env (generates random key B)
process_b_code = """
import sys, os
sys.path.insert(0, os.path.abspath("backend"))
import db

retrieved = db.get_angelone_session()
print("Process B loaded session after restart with auto-generated random Key B:")
print("  - raw retrieved session_token:", retrieved.get("session_token"))
"""

p1 = subprocess.run([sys.executable, "-c", process_a_code], env=UNPINNED_ENV, capture_output=True, text=True)
print(p1.stdout)

p2 = subprocess.run([sys.executable, "-c", process_b_code], env=UNPINNED_ENV, capture_output=True, text=True)
print(p2.stdout)
print("Notice: Without pinned FERNET_KEYS in environment, Process B receives a new key B.")
print("This proves why pinning FERNET_KEYS in environment / HF Space Repository Secrets is required!")
