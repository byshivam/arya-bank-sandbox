"""Planted bugs.

The API is the system under test, so it ships with deliberate defects that
a test suite has to catch. Which bugs are on is decided at start-up:

    ARYA_MODE=practice           # every planted bug on (the Docker image default)
    ARYA_MODE=clean              # no bugs: the "correct" bank to compare against
    PLANTED_BUGS=BUG-01,BUG-04   # exactly these (overrides ARYA_MODE)
    PLANTED_BUGS=all | none

With nothing set the API starts clean, so test suites that run it directly
get a predictable baseline.
"""

from __future__ import annotations

import os

CATALOG: dict[str, dict[str, str]] = {
    "BUG-01": {
        "title": "Idempotency key ignored",
        "impact": "A retried payment (same Idempotency-Key) debits the customer twice.",
    },
    "BUG-02": {
        "title": "Funds check compares whole rupees only",
        "impact": "Balance 500.50 can send 500.90; the account goes negative.",
    },
    "BUG-03": {
        "title": "Negative amounts accepted",
        "impact": "A transfer of -100.00 pulls money from the receiver.",
    },
    "BUG-04": {
        "title": "Transfer can be refunded twice",
        "impact": "Sender gets the money back twice.",
    },
    "BUG-05": {
        "title": "Refund never debits the receiver",
        "impact": "Refund creates money; the double-entry ledger no longer balances.",
    },
    "BUG-06": {
        "title": "Contract drift on account balance",
        "impact": "balance returned as a JSON number (1000.5) instead of a string (\"1000.50\").",
    },
    "BUG-07": {
        "title": "Lost update under concurrent transfers",
        "impact": "Balance is read outside the transaction and written back; parallel payments overwrite each other.",
    },
}


def _parse(raw: str | None) -> frozenset[str]:
    value = (raw or "none").strip()
    if value.lower() in ("", "none", "off", "0"):
        return frozenset()
    if value.lower() == "all":
        return frozenset(CATALOG)
    ids = {part.strip().upper() for part in value.split(",") if part.strip()}
    unknown = ids - set(CATALOG)
    if unknown:
        raise ValueError(f"Unknown planted bug id(s): {', '.join(sorted(unknown))}")
    return frozenset(ids)


def _from_env() -> frozenset[str]:
    explicit = os.environ.get("PLANTED_BUGS")
    if explicit is not None and explicit.strip():
        return _parse(explicit)
    mode = (os.environ.get("ARYA_MODE") or "clean").strip().lower()
    if mode not in ("practice", "clean"):
        raise ValueError(f"ARYA_MODE must be 'practice' or 'clean', got {mode!r}")
    return _parse("all" if mode == "practice" else "none")


ACTIVE: frozenset[str] = _from_env()


def on(bug_id: str) -> bool:
    return bug_id in ACTIVE


def mode() -> str:
    """'practice' (all bugs), 'clean' (none) or 'custom' (a hand-picked PLANTED_BUGS list)."""
    if not ACTIVE:
        return "clean"
    return "practice" if ACTIVE == frozenset(CATALOG) else "custom"
