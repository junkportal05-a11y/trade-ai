#!/bin/sh
# Pre-commit guard: block committing real .env secret files.
# Allows .env.example (placeholders only).
if git diff --cached --name-only | grep -E '(^|/)\.env($|\.)' | grep -v '\.env\.example$'; then
  echo "ERROR: attempt to commit a .env secret file. Aborting commit." >&2
  exit 1
fi
exit 0
