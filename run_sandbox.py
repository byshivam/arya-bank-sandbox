"""Start the whole sandbox: payments API (port 8000) and net banking web app (port 4173).

    python run_sandbox.py                   # practice mode: planted bugs on
    python run_sandbox.py --mode clean      # the bug-free bank, to compare against

This is what the Docker image runs. Both services stop if either one dies.
Settings can also come from the environment (ARYA_MODE, PLANTED_BUGS, UI_BUGS,
ARYA_DB_PATH, ARYA_SEED); command-line flags win.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "services" / "payments-api"
WEB_DIR = ROOT / "services" / "netbanking-web"


def pipe(prefix: str, stream) -> None:
    for line in iter(stream.readline, ""):
        sys.stdout.write(f"[{prefix}] {line}")
        sys.stdout.flush()


def wait_for(url: str, timeout: float = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.3)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["practice", "clean"], default=os.environ.get("ARYA_MODE", "practice"))
    parser.add_argument("--api-port", type=int, default=int(os.environ.get("API_PORT", 8000)))
    parser.add_argument("--web-port", type=int, default=int(os.environ.get("WEB_PORT", 4173)))
    parser.add_argument("--db", default=os.environ.get("ARYA_DB_PATH", str(ROOT / "data" / "arya_payments.db")))
    args = parser.parse_args()

    node = shutil.which("node")
    if not node:
        print("Node.js 20+ is needed for the net banking app (or use the Docker image).", file=sys.stderr)
        return 2

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ARYA_MODE": args.mode, "ARYA_DB_PATH": args.db, "PYTHONUNBUFFERED": "1"}
    env.setdefault("ARYA_SEED", "1")

    procs = {
        "api": subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "arya_payments.main:app", "--app-dir", str(API_DIR),
             "--host", "0.0.0.0", "--port", str(args.api_port), "--log-level", "warning"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True),
        "web": subprocess.Popen(
            [node, str(WEB_DIR / "server.mjs")],
            env={**env, "PORT": str(args.web_port)}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True),
    }
    for name, proc in procs.items():
        threading.Thread(target=pipe, args=(name, proc.stdout), daemon=True).start()

    def stop(*_):
        for proc in procs.values():
            if proc.poll() is None:
                proc.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    ready = wait_for(f"http://127.0.0.1:{args.api_port}/health") and wait_for(f"http://127.0.0.1:{args.web_port}/api/health")
    if ready:
        print(
            "\n  Arya Bank sandbox is up  (fictional bank, synthetic data)\n"
            f"  mode:          {args.mode}{'  - planted bugs are ON, go find them' if args.mode == 'practice' else '  - no planted bugs'}\n"
            f"  Net banking:   http://localhost:{args.web_port}   (login AB10001 / Arya@2026)\n"
            f"  Payments API:  http://localhost:{args.api_port}/docs\n"
            "  Reset data:    POST /_admin/reset (API) and POST /api/_admin/reset (web)\n"
            "  Challenges:    challenges/README.md\n",
            flush=True,
        )

    try:
        while all(p.poll() is None for p in procs.values()):
            time.sleep(0.5)
    finally:
        stop()
        for proc in procs.values():
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    codes = {name: p.returncode for name, p in procs.items()}
    return 0 if all(c in (0, -signal.SIGTERM, -signal.SIGINT) for c in codes.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
