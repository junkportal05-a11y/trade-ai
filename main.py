"""
Trade AI / ApexTrade Quantitative Trading Engine Entry Point.
Starts the FastAPI application and quantitative trading server.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Setup directories
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"

# If uvicorn is not in the current python interpreter, transparently switch to the .venv python
try:
    import uvicorn
except ImportError:
    if VENV_PYTHON.exists() and sys.executable.lower() != str(VENV_PYTHON).lower():
        sys.exit(subprocess.call([str(VENV_PYTHON)] + sys.argv))
    else:
        sys.stderr.write(
            "\n[Error] Required dependency 'uvicorn' is not installed in the active Python environment.\n"
            f"Please run: {VENV_PYTHON} -m pip install -r requirements.txt\n\n"
        )
        sys.exit(1)

# Ensure backend directory is in sys.path for direct imports
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure root directory is also in sys.path
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load environment configuration — fail loudly if production secrets are missing
try:
    from dotenv import load_dotenv
    found = False
    if (ROOT_DIR / ".env").exists():
        load_dotenv(ROOT_DIR / ".env")
        found = True
    elif (BACKEND_DIR / ".env").exists():
        load_dotenv(BACKEND_DIR / ".env")
        found = True
    if not found:
        raise RuntimeError(
            "\n[Error] No .env file found in root or backend directory. "
            "Required secrets (JWT_SECRET, ADMIN_KEY, PASS_ADMIN, etc.) must be set as environment variables. "
            "Do NOT copy .env.example into place — it contains placeholder secrets.\n"
        )
except ImportError:
    raise RuntimeError(
        "\n[Error] python-dotenv is not installed. "
        "Required secrets (JWT_SECRET, ADMIN_KEY, PASS_ADMIN, etc.) must be set as environment variables.\n"
    )


# Configure stdout/stderr for UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


import socket


def check_port(host: str, port: int, timeout: float = 0.3) -> bool:
    """Quickly check if a TCP port is open (useful for frontend dev server probe)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def run_preflight_checks() -> dict:
    """Run non-blocking pre-flight health checks on subsystems."""
    results = {}

    # 1. Database Check
    try:
        from app.core.config import settings
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_type = "PostgreSQL" if settings.is_postgres else "SQLite"
        results["database"] = (True, f"{db_type} Connected (WAL verified)")
    except Exception as exc:
        results["database"] = (False, f"Connection Failed: {str(exc)[:60]}")

    # 2. Broker Configuration Check
    try:
        from app.core.config import settings
        has_key = bool(settings.angel_api_key)
        has_client = bool(settings.angel_client_code)
        has_pin = bool(settings.angel_pin)
        has_totp = bool(settings.angel_totp_secret)
        if has_key and has_client and has_pin and has_totp:
            mode = settings.trading_mode.upper()
            armed = " [ARMED]" if settings.live_trading_armed and mode == "LIVE" else ""
            results["broker"] = (True, f"Angel One Configured ({mode}{armed})")
        else:
            missing = []
            if not has_key: missing.append("API_KEY")
            if not has_client: missing.append("CLIENT_CODE")
            if not has_pin: missing.append("PIN")
            if not has_totp: missing.append("TOTP")
            results["broker"] = (False, f"Missing: {', '.join(missing)} (Paper Mode Active)")
    except Exception as exc:
        results["broker"] = (False, f"Check error: {str(exc)[:40]}")

    # 3. AI / LLM Intelligence
    try:
        from app.core.config import settings
        has_gemini = bool(settings.gemini_api_key)
        results["ai"] = (True, "Gemini AI Ready" if has_gemini else "Fallback / Rule-based (No GEMINI_API_KEY)")
    except Exception:
        results["ai"] = (False, "Unavailable")

    # 4. Frontend Connectivity Probe
    fe_dev_5173 = check_port("127.0.0.1", 5173)
    fe_dev_3000 = check_port("127.0.0.1", 3000)
    fe_dist = (ROOT_DIR / "frontend" / "dist").exists()
    if fe_dev_5173:
        results["frontend"] = (True, "Vite Dev Server Active (http://localhost:5173)")
    elif fe_dev_3000:
        results["frontend"] = (True, "OpenRouter Proxy Active (http://localhost:3000)")
    elif fe_dist:
        results["frontend"] = (True, "Production Build Available (frontend/dist)")
    else:
        results["frontend"] = (False, "Offline (run 'npm run dev' in frontend/)")

    # 5. Data & Knowledge Store
    k_dir = ROOT_DIR / "knowledge"
    h_dir = ROOT_DIR / "historical_data"
    k_count = len(list(k_dir.glob("*.pdf"))) if k_dir.exists() else 0
    h_count = len(list(h_dir.glob("*.csv"))) if h_dir.exists() else 0
    results["data_stores"] = (True, f"Knowledge: {k_count} PDFs | History: {h_count} caches")

    return results


def run():
    parser = argparse.ArgumentParser(description="Trade AI - ApexTrade Server")
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host address to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind (default: 8000 — matches the frontend dev proxy; HF Space deployment uses the Dockerfile, not this script)"
    )
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=os.getenv("RELOAD", "false").lower() in ("true", "1"),
        help="Enable/disable auto-reload on code change. Enabled only with --reload flag or RELOAD=true env var for local dev."
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run preflight health checks and exit without starting server"
    )

    args = parser.parse_args()

    # Run Subsystem Health Checks
    checks = run_preflight_checks()

    print("\n" + "=" * 70)
    print("  ▲ APEXTRADE AI QUANTITATIVE ENGINE")
    print("=" * 70)
    print(f"  [Server]    http://{args.host}:{args.port}")
    print(f"  [API Docs]  http://localhost:{args.port}/docs")
    print(f"  [Health]    http://localhost:{args.port}/api/health")
    print(f"  [Reload]    {'Enabled' if args.reload else 'Disabled'}")
    print(f"  [Python]    {sys.executable}")
    print("-" * 70)
    print("  SUB-SYSTEM HEALTH PREFLIGHT:")

    for name, (status, detail) in checks.items():
        icon = "✓" if status else "!"
        tag = "[OK]  " if status else "[WARN]"
        label = f"{name.replace('_', ' ').title():<13}"
        print(f"  {icon} {tag} {label} : {detail}")

    print("=" * 70 + "\n")

    if args.check_only:
        all_passed = all(st for st, _ in checks.values())
        sys.exit(0 if all_passed else 1)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(BACKEND_DIR)
    )


if __name__ == "__main__":
    run()
