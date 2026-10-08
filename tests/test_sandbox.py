"""Tests for the sandbox itself (not the planted bugs - those are for learners to find).

They start the real launcher (run_sandbox.py) on free ports and check the
things learners rely on: modes, seed data, reset, and the ledger invariants.

    pip install -r services/payments-api/requirements.txt pytest
    pytest -q
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "payments-api"))
from arya_payments import seed  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def call(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw, status, kind = r.read().decode(), r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw, status, kind = e.read().decode(), e.code, e.headers.get("Content-Type", "")
    return status, (json.loads(raw) if raw and "json" in kind else raw)


class Sandbox:
    def __init__(self, tmp: Path, mode: str = "clean", **env: str):
        self.api_port, self.web_port = free_port(), free_port()
        self.db = tmp / f"sandbox-{uuid.uuid4().hex[:6]}.db"
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "run_sandbox.py"), "--mode", mode, "--api-port", str(self.api_port),
             "--web-port", str(self.web_port), "--db", str(self.db)],
            env={**{k: v for k, v in os.environ.items() if k not in ("PLANTED_BUGS", "UI_BUGS", "ARYA_MODE")}, **env},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("sandbox exited:\n" + self.proc.stdout.read())
            try:
                if call(self.api + "/health")[0] == 200 and call(self.web + "/api/health")[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.3)
        self.stop()
        raise RuntimeError("sandbox did not start in time")

    @property
    def api(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    @property
    def web(self) -> str:
        return f"http://127.0.0.1:{self.web_port}"

    def sql(self, query: str) -> list[tuple]:
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(query).fetchall()
        finally:
            conn.close()

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    box = Sandbox(tmp_path_factory.mktemp("clean"), "clean")
    yield box
    box.stop()


@pytest.fixture(scope="module")
def practice(tmp_path_factory):
    box = Sandbox(tmp_path_factory.mktemp("practice"), "practice")
    yield box
    box.stop()


def assert_ledger_ok(box: Sandbox) -> None:
    unbalanced = box.sql(
        "SELECT txn_id FROM ledger_entries GROUP BY txn_id "
        "HAVING SUM(CASE direction WHEN 'DEBIT' THEN amount_paise ELSE -amount_paise END) != 0")
    out_of_sync = box.sql(
        "SELECT a.account_id FROM accounts a LEFT JOIN (SELECT account_id, "
        "SUM(CASE direction WHEN 'CREDIT' THEN amount_paise ELSE -amount_paise END) n "
        "FROM ledger_entries GROUP BY account_id) l USING (account_id) WHERE a.balance_paise != COALESCE(l.n, 0)")
    total = box.sql("SELECT SUM(balance_paise) FROM accounts")[0][0]
    negative = box.sql("SELECT account_id FROM accounts WHERE kind = 'CUSTOMER' AND balance_paise < 0")
    assert (unbalanced, out_of_sync, total, negative) == ([], [], 0, [])


# ------------------------------------------------------------------ modes


def test_clean_mode_has_no_bugs(clean):
    assert call(clean.api + "/health")[1] == {"status": "UP", "mode": "clean", "planted_bugs": []}
    assert call(clean.web + "/api/health")[1] == {"status": "UP", "mode": "clean", "plantedBugs": []}
    assert 'data-bugs=""' in call(clean.web + "/login")[1]


def test_practice_mode_turns_every_bug_on(practice):
    api = call(practice.api + "/health")[1]
    web = call(practice.web + "/api/health")[1]
    assert api["mode"] == "practice" and len(api["planted_bugs"]) == 7
    assert web["mode"] == "practice" and len(web["plantedBugs"]) == 9
    assert 'data-bugs="UI-01 UI-02' in call(practice.web + "/login")[1]


def test_explicit_bug_list_overrides_mode(tmp_path):
    box = Sandbox(tmp_path, "practice", PLANTED_BUGS="BUG-03", UI_BUGS="UI-05")
    try:
        assert call(box.api + "/health")[1]["planted_bugs"] == ["BUG-03"]
        assert call(box.api + "/health")[1]["mode"] == "custom"
        assert call(box.web + "/api/health")[1]["plantedBugs"] == ["UI-05"]
    finally:
        box.stop()


# ------------------------------------------------------------------ seed data


def test_seed_is_synthetic_and_deterministic(clean):
    planned = seed.plan_accounts()
    for acct in planned[:5]:
        status, body = call(f"{clean.api}/accounts/{acct.account_id}")
        assert status == 200 and body["holder_name"] == acct.holder_name
    assert len(clean.sql("SELECT 1 FROM accounts WHERE kind = 'CUSTOMER'")) == seed.DEFAULT_CUSTOMERS
    assert seed.plan_accounts() == planned  # same seed, same people


def test_seed_keeps_the_ledger_balanced(clean):
    assert clean.sql("SELECT COUNT(*) FROM transfers WHERE kind = 'TRANSFER'")[0][0] > 40
    assert_ledger_ok(clean)


def test_seed_csv_export(tmp_path):
    out = tmp_path / "accounts.csv"
    assert seed.main(["--csv", str(out), "--customers", "3"]) == 0
    lines = out.read_text().splitlines()
    assert lines[0] == "account_id,holder_name,opening_balance" and len(lines) == 4


# ------------------------------------------------------------------ reset


def test_api_reset_restores_the_seed(clean):
    before = clean.sql("SELECT account_id, holder_name, balance_paise FROM accounts ORDER BY seq")
    first, second = before[1][0], before[2][0]
    status, _ = call(clean.api + "/transfers", "POST", {"from_account": first, "to_account": second, "amount": "10.00"},
                     {"Idempotency-Key": uuid.uuid4().hex})
    assert status == 201
    assert call(clean.api + "/accounts", "POST", {"holder_name": "Temp", "opening_balance": "5.00"})[0] == 201
    assert clean.sql("SELECT account_id, holder_name, balance_paise FROM accounts ORDER BY seq") != before

    status, body = call(clean.api + "/_admin/reset", "POST")
    assert status == 200 and body["status"] == "RESET"
    assert clean.sql("SELECT account_id, holder_name, balance_paise FROM accounts ORDER BY seq") == before
    assert_ledger_ok(clean)


def test_web_reset_restores_the_demo_customer(clean):
    req = urllib.request.Request(clean.web + "/api/login", method="POST",
                                 data=json.dumps({"customerId": "AB10001", "password": "Arya@2026"}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        cookie = r.headers["Set-Cookie"].split(";")[0]
    auth = {"Cookie": cookie}
    balance = call(clean.web + "/api/accounts", headers=auth)[1]["accounts"][0]["balance"]
    status, _ = call(clean.web + "/api/transfers", "POST",
                     {"fromAccount": "ACC-100201", "beneficiaryId": "BEN-1", "amount": "100.00"},
                     {**auth, "Idempotency-Key": uuid.uuid4().hex})
    assert status == 201

    assert call(clean.web + "/api/_admin/reset", "POST")[0] == 200
    assert call(clean.web + "/api/accounts", headers=auth)[0] == 401  # sessions are cleared too
    with urllib.request.urlopen(req) as r:
        auth = {"Cookie": r.headers["Set-Cookie"].split(";")[0]}
    assert call(clean.web + "/api/accounts", headers=auth)[1]["accounts"][0]["balance"] == balance


def test_admin_endpoints_can_be_switched_off(tmp_path):
    box = Sandbox(tmp_path, "clean", ARYA_ADMIN="0")
    try:
        assert call(box.api + "/_admin/reset", "POST")[0] == 404
        assert call(box.web + "/api/_admin/reset", "POST")[0] in (401, 404)  # falls through to the login check
    finally:
        box.stop()


def test_swagger_docs_are_served(clean):
    status, body = call(clean.api + "/openapi.json")
    assert status == 200 and "/transfers" in body["paths"] and "/_admin/reset" in body["paths"]


def test_bad_mode_is_rejected(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "uvicorn", "arya_payments.main:app", "--app-dir", str(ROOT / "services" / "payments-api"),
         "--port", str(free_port())],
        env={**os.environ, "ARYA_MODE": "chaos", "ARYA_DB_PATH": str(tmp_path / "x.db")},
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode != 0 and "ARYA_MODE" in proc.stderr
