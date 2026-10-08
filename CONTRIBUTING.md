# Contributing

Thanks for helping! This sandbox is for testers to learn on, so contributions that make it a better
practice ground are the most welcome: new endpoints, new planted bugs, new challenges, better hints,
starter test suites, docs and translations.

New here? Look for issues labelled
[`good first issue`](https://github.com/byshivam/arya-bank-sandbox/labels/good%20first%20issue).
Comment on one to claim it, so two people don't do the same work.

## Set up

```bash
git clone https://github.com/<you>/arya-bank-sandbox && cd arya-bank-sandbox
pip install -r services/payments-api/requirements.txt pytest
python run_sandbox.py --mode clean       # or practice
pytest -q                                # the sandbox's own tests
```

You need Python 3.10+ and Node 20+. Or open the repo in Codespaces, where everything is installed.

## The three rules

1. **Clean mode must be correct.** With `ARYA_MODE=clean`, every feature should behave the way a real
   bank would. Bugs only exist behind a switch.
2. **Synthetic data only.** No real names from your contacts, no real-looking card or bank account numbers,
   no real IFSC codes. Use Faker and Arya Bank's own formats (`AB000123`, `ACC-100201`, `ARYB...`).
3. **Don't break the existing challenges.** Changing how a planted bug behaves breaks people's test
   suites. If you must, say so in the PR and the CHANGELOG.

## Adding a planted bug

A good planted bug is one that **real teams ship**: rounding, retries, races, missing checks, contract drift,
accessibility gaps. It should be findable with a reasonable test, and it should teach something.

**API bug** (`services/payments-api`)

1. Add an entry to `CATALOG` in `arya_payments/bugs.py` with the next id (`BUG-08`), a title and the impact.
2. Put the faulty behaviour behind `if bugs.on("BUG-08"):` and keep the correct path as the default.
3. Add a challenge (hint only) to `challenges/README.md` and the answer to `challenges/ANSWERS.md`.

**Web app bug** (`services/netbanking-web`)

1. Add an entry to `CATALOG` in `bugs.mjs` (`UI-10`).
2. The server stamps active ids on `<html data-bugs="...">`. In page scripts use `BUGS.has("UI-10")`;
   in CSS use `html[data-bugs~="UI-10"]`. Server-side, check `BUGS.has("UI-10")` in `server.mjs`.
3. Add the challenge and the answer.

Update the bug count in `README.md` and the test in `tests/test_sandbox.py` that counts bugs.

## Adding an endpoint or page

- Follow the existing style: money as strings with two decimals (stored as integer paise), errors as
  `{"error": {"code": "...", "message": "..."}}`, every money movement through the ledger.
- Add the endpoint to the table in `README.md`.
- If it creates data, make sure `POST /_admin/reset` (API) or `resetData()` (web) restores it.
- Add a test for it in `tests/test_sandbox.py` if it touches modes, seed or reset.

## Adding a challenge

A challenge is a short title, a difficulty (⭐ to ⭐⭐⭐) and a hint that says **where to look and what kind
of testing helps**, never what the bug is. The answer goes in `ANSWERS.md` with a way to reproduce it and
the kind of test that catches it.

## Pull requests

- One change per PR, with a short description of what and why.
- `pytest -q` passes, and the sandbox still starts with `python run_sandbox.py`.
- CI also runs two full test suites against your change. If one fails, the PR description should
  explain why (for example, you deliberately changed a bug).
- Be nice in reviews. Everyone here is learning, including the maintainer.

## Recognising contributors

Every kind of contribution counts: code, docs, ideas, bug reports, tutorials. Comment on your merged PR with

```
@all-contributors please add @your-username for code, doc
```

and the bot will add you to the README.
