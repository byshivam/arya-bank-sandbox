# Answers (spoilers!)

Try [the challenges](README.md) first.

Each answer gives the bug id (the one you'd use with `PLANTED_BUGS` / `UI_BUGS`), what goes wrong,
a quick way to reproduce it, and the kind of test that catches it for good.

The commands below use account ids from the seed data. Reset first so your ids match:
`curl -X POST localhost:8000/_admin/reset`.

---

## Payments API

### A1 · BUG-01 · Idempotency key ignored

A retried payment with the same `Idempotency-Key` is processed again, so the customer is debited twice.
Expected: the second call returns the original transfer (`200`, header `Idempotent-Replayed: true`).

```bash
for i in 1 2; do
  curl -s -X POST localhost:8000/transfers -H 'Content-Type: application/json' -H 'Idempotency-Key: retry-1' \
    -d '{"from_account":"AB000002","to_account":"AB000003","amount":"100.00"}'; echo
done   # two different transfer_ids in practice mode
```

**Caught by:** an API test that sends the same request twice and checks there is one transfer and one debit.

### A2 · BUG-02 · Funds check compares whole rupees only

The balance check ignores paise: with ₹500.50 you can send ₹500.90 and the account goes negative.

**Reproduce:** open an account with `"opening_balance": "500.50"` and send `"500.90"` from it. Expected `422 INSUFFICIENT_FUNDS`.

**Caught by:** boundary-value tests around the balance (balance, balance + 0.01) and a DB check that no customer balance is below zero.

### A3 · BUG-03 · Negative amounts accepted

`"amount": "-100.00"` is accepted, so a "transfer" pulls money out of the receiver's account.

**Caught by:** negative and invalid-format amount tests (`-1`, `0`, `0.001`, `1e3`, `" 10"`, `"10,00"`).

### A4 · BUG-04 · A transfer can be refunded twice

The second `POST /transfers/{id}/refund` succeeds again instead of returning `409 ALREADY_REFUNDED`. The sender gets the money back twice.

**Caught by:** an API test that refunds the same transfer twice.

### A5 · BUG-05 · Refund never debits the receiver

The refund credits the sender but never takes the money from the receiver, and writes only the CREDIT ledger leg. The API returns `201` and looks perfectly happy: **money is created out of nothing**.

**Reproduce:** note both balances, transfer, refund, and compare. Or in SQL:

```sql
SELECT txn_id FROM ledger_entries GROUP BY txn_id
HAVING SUM(CASE direction WHEN 'DEBIT' THEN amount_paise ELSE -amount_paise END) != 0;
```

**Caught by:** database / reconciliation checks. Response-only API tests usually miss this one, which is the lesson.

### A6 · BUG-06 · Contract drift on account balance

`GET /accounts/{id}` returns `"balance": 1000.5` (a JSON number) instead of `"balance": "1000.50"` (a string). A mobile app parsing it as a string would crash, and floats lose paise.

**Caught by:** consumer-driven contract tests (Pact) or a JSON schema check on every response.

### A7 · BUG-07 · Lost update under concurrent transfers

Balances are read outside the database transaction and written back as absolute values, so parallel payments overwrite each other. One at a time, everything is fine.

**Reproduce:** fire 20 transfers of ₹1.00 from one account in parallel. In practice mode the sender's balance drops by only a few rupees instead of ₹20.00, while the ledger records all 20 debits, so the balance and the ledger disagree. In clean mode it drops by exactly ₹20.00.

```bash
seq 1 20 | xargs -P 20 -I{} curl -s -o /dev/null -X POST localhost:8000/transfers \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: rush-{}' \
  -d '{"from_account":"AB000002","to_account":"AB000003","amount":"1.00"}'
```

Note that the *sum* of the two accounts still looks right (both sides are overwritten from the same stale read), so a "total is unchanged" check on just those two accounts misses it.

**Caught by:** a concurrency test (thread pool + latch) that checks the exact balance afterwards, the ledger rule "balance = credits - debits", or a load test across many accounts with a money-conservation check (k6 thresholds).

---

## Net banking web app

### W1 · UI-01 · Confirm button has no accessible name

On the transfer review step, Confirm shows only a ✓ icon. A screen reader announces just "button".

**Caught by:** axe-core (`button-name` rule) on the review step, or a `getByRole('button', { name: /confirm/i })` locator that suddenly can't find it.

### W2 · UI-02 · Login error text fails colour contrast

The error message is light grey on white (about 1.9:1). WCAG 2.2 AA needs 4.5:1 for normal text.

**Caught by:** axe-core `color-contrast` on the login page *after* a failed login. Scanning only the empty page misses it.

### W3 · UI-03 · Paise dropped from the amount

Type `1500.75`: the review shows ₹1,500.00 and ₹1,500.00 is sent. The customer pays a different amount than they typed.

**Caught by:** an E2E test that checks the amount on the review step, the success message *and* the statement, with an amount that has paise.

### W4 · UI-04 · Mobile layout overflow

Below 600 px the account cards are fixed at 520 px wide, the page scrolls sideways and Send money is pushed off-screen.

**Caught by:** a responsive test on a phone viewport that checks `document.documentElement.scrollWidth <= window.innerWidth` and that key buttons are in view.

### W5 · UI-05 · Double submit on Confirm

Confirm stays enabled and every click sends a new request with a new idempotency key. A double tap pays twice.

**Caught by:** a test that double-clicks Confirm (or clicks twice fast) and checks the statement has exactly one new debit.

### W6 · UI-06 · Failed transfer shown as success

If the transfer API errors or the network drops, the page still says "Transfer successful".

**Caught by:** network mocking (`page.route('**/api/transfers', r => r.fulfill({ status: 500 }))` or `r.abort()`) and checking the error message is shown.

### W7 · UI-07 · Beneficiary form has no labels

The add-beneficiary inputs only have placeholder text, so screen readers can't name them.

**Caught by:** axe-core (`label` rule), or `getByLabel('Account number')` failing.

### W8 · UI-08 · Logout keeps the session

Logout only redirects to the login page. The session cookie stays valid and `/dashboard` opens again.

**Caught by:** an E2E test that logs out and then visits `/dashboard` (or calls `/api/accounts`) expecting to be sent back to login / get `401`.

### W9 · UI-09 · Statement uses a Chromium-only API

The statement page uses `navigator.userAgentData`, which doesn't exist in Firefox and Safari, so the statement never loads there.

**Caught by:** running the same tests on Firefox and WebKit, not only Chromium.

---

Know a better way to catch one of these? Share it in
[Discussions](https://github.com/byshivam/arya-bank-sandbox/discussions).
