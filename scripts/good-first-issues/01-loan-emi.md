title: Add a loan EMI calculator endpoint
labels: good first issue, enhancement, payments-api
---
Add `POST /loans/emi` to the payments API: given `principal` ("500000.00"), `annual_rate` ("10.50") and `months` (60), return the monthly EMI and the total interest, as money strings.

**Done when**
- Uses the standard EMI formula, rounded to paise at the end (not at each step)
- Validation: principal > 0, rate 0–36, months 1–360, errors in the usual `{"error": {...}}` shape
- A test in `tests/test_sandbox.py`
- Listed in the README endpoint table

Bonus (separate PR): a planted rounding bug behind `BUG-08`, plus a challenge and answer.
