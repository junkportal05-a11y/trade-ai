#!/usr/bin/env python3
"""Generate a fresh JWT_SECRET and write it to backend/.env (gitignored).

The new value is written only to backend/.env (which is gitignored). It is
intentionally NOT printed, to avoid exposing credentials in logs/transcripts.
Open backend/.env and copy the JWT_SECRET line into the HF Space
"Variables and secrets" setting. Rotating invalidates existing sessions/tokens
on any deployment that still uses the old value.
"""
import os
import re
import secrets
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, "backend", ".env")

new_secret = secrets.token_hex(32)

if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    if re.search(r"^JWT_SECRET=", content, re.MULTILINE):
        content = re.sub(
            r"^JWT_SECRET=.*$", f"JWT_SECRET={new_secret}", content, flags=re.MULTILINE
        )
    else:
        content += f"\nJWT_SECRET={new_secret}\n"
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated JWT_SECRET in {ENV_PATH}")
    print("Open that file and copy the JWT_SECRET value into the HF Space secret store.")
else:
    print(f"WARNING: {ENV_PATH} not found; refusing to create it.", file=sys.stderr)
