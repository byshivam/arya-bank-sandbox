"""Synthetic seed data for the sandbox (Faker, fixed seed).

Everything here is made up: Faker names, account ids in Arya Bank's own
AB000000 format, and fake money. No real person, card or bank number is ever
generated, so the data is safe to share, screenshot and break.

The same seed always produces the same customers, balances and history, so a
learner who finds a bug can describe it with ids everyone else also has.

Every rupee is moved through the double-entry ledger, exactly like the API
does it, so the ledger invariants hold right after seeding:
  * each txn_id: total DEBIT == total CREDIT
  * each account: balance == credits - debits
  * all balances, including the funding account AB000000, sum to 0.00

Used by the API (ARYA_SEED=1 at start-up, and POST /_admin/reset). Also a CLI:

    python -m arya_payments.seed --csv accounts.csv     # export what would be seeded
"""

from __future__ import annotations

import argparse
import csv
import random
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import db

SEED = 2026
DEFAULT_CUSTOMERS = 25
DEFAULT_TRANSFERS = 60
DEFAULT_REFUNDS = 4
HISTORY_START = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
REMARKS = [
    "Rent", "Dinner split", "Electricity bill", "Groceries", "Movie tickets", "School fees",
    "Gift", "Loan repayment", "Trip share", "Gym membership", None, None,
]


@dataclass(frozen=True)
class SeedAccount:
    account_id: str
    holder_name: str
    opening_paise: int


def _ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _people(count: int) -> list[str]:
    from faker import Faker  # imported here so the API runs without Faker when seeding is off

    fake = Faker("en_IN")
    fake.seed_instance(SEED)
    names: list[str] = []
    while len(names) < count:
        name = f"{fake.first_name()} {fake.last_name()}"
        if name not in names:
            names.append(name)
    return names


def plan_accounts(count: int = DEFAULT_CUSTOMERS) -> list[SeedAccount]:
    """The customers the seed will create. Ids assume a fresh database."""
    rng = random.Random(SEED)
    accounts = []
    for i, name in enumerate(_people(count)):
        # Mostly everyday balances, a few large ones, always with paise so rounding bugs show.
        rupees = rng.choice([rng.randint(500, 25_000), rng.randint(25_000, 2_50_000), rng.randint(2_50_000, 9_00_000)])
        accounts.append(SeedAccount(f"AB{i + 2:06d}", name, rupees * 100 + rng.randint(0, 99)))
    return accounts


def _seed_id(rng: random.Random, prefix: str) -> str:
    return prefix + f"{rng.getrandbits(48):012X}"


def seed(conn: sqlite3.Connection, customers: int = DEFAULT_CUSTOMERS, transfers: int = DEFAULT_TRANSFERS,
         refunds: int = DEFAULT_REFUNDS) -> dict:
    """Write the seed into an empty database (after db.init). Runs inside the caller's transaction."""
    rng = random.Random(SEED + 1)
    clock = HISTORY_START
    balances: dict[str, int] = {}

    for acct in plan_accounts(customers):
        stamp = _ts(clock)
        cur = conn.execute(
            "INSERT INTO accounts (holder_name, balance_paise, created_at) VALUES (?, ?, ?)",
            (acct.holder_name, acct.opening_paise, stamp),
        )
        account_id = f"AB{cur.lastrowid:06d}"
        conn.execute("UPDATE accounts SET account_id = ? WHERE seq = ?", (account_id, cur.lastrowid))
        conn.execute(
            "UPDATE accounts SET balance_paise = balance_paise - ? WHERE account_id = ?",
            (acct.opening_paise, db.SYSTEM_ACCOUNT),
        )
        _entries(conn, f"OPEN-{account_id}", db.SYSTEM_ACCOUNT, account_id, acct.opening_paise, stamp)
        balances[account_id] = acct.opening_paise
        clock += timedelta(minutes=7)

    ids = list(balances)
    done: list[tuple[str, str, str, int]] = []
    for _ in range(transfers):
        payer, payee = rng.sample(ids, 2)
        cap = min(balances[payer] // 5, 50_000_00)  # at most a fifth of the balance, ₹50,000
        if cap < 100:
            continue
        paise = rng.randint(100, cap)
        clock += timedelta(hours=rng.randint(2, 11), minutes=rng.randint(0, 59))
        stamp, transfer_id = _ts(clock), _seed_id(rng, "TXN")
        _move(conn, balances, payer, payee, paise)
        conn.execute(
            "INSERT INTO transfers (transfer_id, kind, from_account, to_account, amount_paise, status, remarks, created_at) "
            "VALUES (?, 'TRANSFER', ?, ?, ?, 'COMPLETED', ?, ?)",
            (transfer_id, payer, payee, paise, rng.choice(REMARKS), stamp),
        )
        _entries(conn, transfer_id, payer, payee, paise, stamp)
        done.append((transfer_id, payer, payee, paise))

    refunded = 0
    for transfer_id, payer, payee, paise in rng.sample(done, min(refunds, len(done))):
        if balances[payee] < paise:
            continue
        clock += timedelta(hours=3)
        stamp, refund_id = _ts(clock), _seed_id(rng, "RFD")
        _move(conn, balances, payee, payer, paise)
        conn.execute(
            "INSERT INTO transfers (transfer_id, kind, from_account, to_account, amount_paise, status, refund_of, created_at) "
            "VALUES (?, 'REFUND', ?, ?, ?, 'COMPLETED', ?, ?)",
            (refund_id, payee, payer, paise, transfer_id, stamp),
        )
        conn.execute("UPDATE transfers SET status = 'REFUNDED', refund_id = ? WHERE transfer_id = ?", (refund_id, transfer_id))
        _entries(conn, refund_id, payee, payer, paise, stamp)
        refunded += 1

    return {"customers": len(ids), "transfers": len(done), "refunds": refunded}


def _move(conn: sqlite3.Connection, balances: dict[str, int], payer: str, payee: str, paise: int) -> None:
    conn.execute("UPDATE accounts SET balance_paise = balance_paise - ? WHERE account_id = ?", (paise, payer))
    conn.execute("UPDATE accounts SET balance_paise = balance_paise + ? WHERE account_id = ?", (paise, payee))
    balances[payer] -= paise
    balances[payee] += paise


def _entries(conn: sqlite3.Connection, txn_id: str, debit: str, credit: str, paise: int, stamp: str) -> None:
    for account_id, direction in ((debit, "DEBIT"), (credit, "CREDIT")):
        conn.execute(
            "INSERT INTO ledger_entries (txn_id, account_id, direction, amount_paise, created_at) VALUES (?, ?, ?, ?, ?)",
            (txn_id, account_id, direction, paise, stamp),
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the sandbox's synthetic customers as CSV.")
    parser.add_argument("--csv", default="-", help="output file (default: stdout)")
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    args = parser.parse_args(argv)
    out = sys.stdout if args.csv == "-" else open(args.csv, "w", newline="", encoding="utf-8")
    try:
        writer = csv.writer(out)
        writer.writerow(["account_id", "holder_name", "opening_balance"])
        for acct in plan_accounts(args.customers):
            writer.writerow([acct.account_id, acct.holder_name, f"{acct.opening_paise // 100}.{acct.opening_paise % 100:02d}"])
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
