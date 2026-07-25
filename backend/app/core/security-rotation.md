---
title: "Fernet Key Rotation Procedure"
tags: ["security", "cryptography", "operations"]
date: 2025-09-28
description: "This note outlines the secure process for rotating Fernet encryption keys, preserving data integrity, supporting multi‑key decryption, and providing rollback capabilities."
---

# Fernet Key Rotation Procedure

## Objective
Safely rotate the Fernet encryption key used to protect sensitive broker credentials without losing access to data that was encrypted with the previous key. The process must:

* Preserve existing encrypted values.  
* Allow both old and new keys to be used for decryption during the transition.  
* Complete the migration with minimal downtime.  
* Verify that the new key works correctly before de‑commissioning the old one.  

[[config.md]]
[[architecture.md]]

## 1. Prerequisites

| Item | Details |
|------|---------|
| **Python version** | ≥ 3.9 (type‑hints used) |
| **Dependencies** | `cryptography>=42.0.0` (for `Fernet` and `MultiFernet`) |
| **Configuration** | `fernet_keys` list added to `Settings` (see *config.py*). |
| **Code changes** | Modified `security.py` to load keys via `MultiFernet`. |
| **Backup** | Snapshot of the database / files that contain encrypted data. |
| **Test environment** | Replicate production setup (same env vars, same `settings` instance). |

---

## 2. Generate a New Key

```python
# In a REPL, management command, or ad‑hoc script
import secrets

new_key = secrets.token_urlsafe(32)   # 32‑byte URL‑safe value → 43‑char string
print(new_key)   # store this value securely; you’ll add it to the config
```

**Store the new key** somewhere safe (e.g., a temporary file or env var). It will be inserted into `settings.fernet_keys` in the next step.

---

## 3. Update `config.py`

Add a **list** of Fernet keys to the `Settings` model and migrate the existing single‑key field.

```python
# Existing imports …
from typing import List, Literal   # <-- ensure List is imported

# Existing fields …
jwt_secret: str = Field(default_factory=lambda: secrets.token_hex(32), alias="JWT_SECRET")
# fernet_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), alias="FERNET_KEY")   # <-- keep if you want a fallback

# NEW: list of keys (default contains the current key)
fernet_keys: List[str] = Field(
    default_factory=lambda: [settings.fernet_key],
    alias="FERNET_KEYS"
)

# Keep the original single‑key field if you want a graceful fallback, or remove it after migration:
# fernet_key: str = ...   # optional, can be removed after migration
```

*The new key should be appended to the list; the existing key remains the first element so that decryption of legacy data still works.*

The module already builds the Fernet objects from `settings.fernet_keys` (see `security.py`).

---

## 4. Update `security.py` to Use `MultiFernet`

Replace the single `Fernet` instance with a `MultiFernet` that wraps all keys in `settings.fernet_keys`.

```python
# At the top of security.py (after imports)
from cryptography.fernet import Fernet, MultiFernet
from app.core.config import settings

# Build a list of Fernet objects, one per key
_fernet_list = [Fernet(key) for key in settings.fernet_keys]
_fernet = MultiFernet(_fernet_list)   # can now decrypt with any of the keys
```

Update the helper functions:

```python
def encrypt_value(plaintext: str | None) -> str | None:
    """Encrypt a sensitive string for storage. Returns base64 ciphertext."""
    if plaintext is None:
        return None
    # First key in the list is used for encryption of new data
    return _fernet.encrypt(plaintext.encode()).decode()

def decrypt_value(ciphertext: str | None) -> str | None:
    """Decrypt a Fernet‑encrypted string."""
    if ciphertext is None:
        return None
    try:
        # MultiFernet will try each Fernet in order until one succeeds
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        return None
```

All other code that referenced `_fernet.decrypt` or `_fernet.encrypt` can stay unchanged because the `_fernet` object now implements multi‑key behaviour.

---

## 5. Deploy and Verify

1. **Deploy the code changes** (updated `config.py` and `security.py`).  
2. **Restart the application** so `settings` is re‑initialized and the new key list is active.  
3. **Create a test record**: encrypt a fresh piece of data (e.g., a dummy broker API secret). Verify that decryption works immediately.  
4. **Simulate a legacy record**: take an existing ciphertext that was encrypted with the old key, attempt to decrypt it using the updated code. It should succeed because `MultiFernet` tries each key in order.  
5. **Confirm both operations** succeed in a staging environment before promoting to production.

---

## 6. Migrate Existing Data (Optional, Recommended)

If you want newly‑encrypted data to use only the new key, run a one‑time migration script:

```python
# migration_script.py
from app.core.config import settings
from app.core.security import _fernet  # the global MultiFernet instance

def migrate_record(encrypted_blob: str) -> str:
    # Decrypt with the old key (first in the list)
    raw = _fernet.decrypt(encrypted_blob.encode()).decode()
    # Re‑encrypt with the new key (last in the list, or a stored new_key)
    new_key = settings.fernet_keys[-1]  # or use a stored variable
    return Fernet(new_key).encrypt(raw.encode()).decode()

# Iterate over your storage (DB rows, files, etc.) and replace the old ciphertext
# with the value returned by `migrate_record`.
```

**Steps:**

1. Pull each encrypted value (e.g., broker API secret) from the data store.  
2. Call `migrate_record` to produce a new ciphertext encrypted with the **new** key.  
3. Write the new ciphertext back, overwriting the old one.  
4. Once all records are migrated, you can safely drop the earlier keys from `fernet_keys` (e.g., keep only the newest one).  

---

## 7. Clean‑up After Migration

1. **Remove the deprecated single‑key field** (if you kept it) from `config.py`.  
2. **Trim the `fernet_keys` list** to contain only the desired active key(s).  
   ```python
   fernet_keys: List[str] = Field(default_factory=lambda: [new_key], alias="FERNET_KEYS")
   ```
3. **Restart** the application one final time.  
4. **Delete or archive** the old key securely (e.g., encrypted backup for audit purposes).  

---

## 8. Rollback Plan

*If any step fails*:

1. Re‑insert the previous key as the **first** element of `fernet_keys`.  
2. Redeploy and restart the service.  
3. All previously encrypted data will decrypt correctly again, and new data will continue to use the old key.  

Having the old key still present in the list guarantees that decryption of legacy data never fails, providing a safe rollback path.

---

## 9. Checklist

- [ ] New key generated (`secrets.token_urlsafe(32)`).  
- [ ] `fernet_keys` list updated in `config.py` (contains both old and new).  
- [ ] `security.py` imports `MultiFernet` and builds `_fernet`.  
- [ ] Encryption/decryption functions now rely on `_fernet`.  
- [ ] Application restarted and logs show successful load of new settings.  
- [ ] Tested encryption of fresh data & decryption of historic data.  
- [ ] Migration script executed (if opting to re‑encrypt existing records).  
- [ ] Documentation updated (this file).  
- [ ] Production deployment performed with monitoring for errors.  
- [ ] Post‑deployment verification that all secret brokers can still be read/written.  
- [ ] Old key securely archived and plan for eventual deletion.  

---  

*End of document.*  

[[config.md]]