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

# Load environment configuration (.env from root or backend)
try:
    from dotenv import load_dotenv
    if (ROOT_DIR / ".env").exists():
        load_dotenv(ROOT_DIR / ".env")
    elif (BACKEND_DIR / ".env").exists():
        load_dotenv(BACKEND_DIR / ".env")
    elif (ROOT_DIR / ".env.example").exists():
        load_dotenv(ROOT_DIR / ".env.example")
except ImportError:
    pass


# Configure stdout/stderr for UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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
        default=int(os.getenv("PORT", "7860")),
        help="Port to bind (default: 7860)"
    )
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=os.getenv("RELOAD", "true").lower() in ("true", "1"),
        help="Enable/disable auto-reload on code change"
    )

    args = parser.parse_args()

    print("=" * 65)
    print(" [*] Trade AI / ApexTrade Quantitative Trading Engine")
    print(f" [*] Running on: http://{args.host}:{args.port}")
    print(f" [*] Project Root: {ROOT_DIR}")
    print(f" [*] Backend Path: {BACKEND_DIR}")
    print(f" [*] Python Env:  {sys.executable}")
    print(f" [*] Auto-Reload: {args.reload}")
    print(f" [*] Interactive API Docs: http://localhost:{args.port}/docs")
    print("=" * 65)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(BACKEND_DIR)
    )


if __name__ == "__main__":
    run()
