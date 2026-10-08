# Find the 16 bugs

Start the sandbox in **practice mode** (the default) and hunt. Each challenge tells you where to
look and what kind of testing finds it, not what the bug is. Answers are in [ANSWERS.md](ANSWERS.md),
but try first.

**How to prove a find:** reproduce it in practice mode, then show the same steps behave correctly in
clean mode (`-e ARYA_MODE=clean`). A bug report with both is a good bug report.

**Reset any time:** `curl -X POST localhost:8000/_admin/reset` (API) and
`curl -X POST localhost:4173/api/_admin/reset` (web).

Difficulty: ⭐ plain requests · ⭐⭐ you need to check the data, not just the response · ⭐⭐⭐ needs a special tool or setup

---

## Payments API (port 8000): 7 bugs

Use Swagger at http://localhost:8000/docs, curl, Postman, or code (RestAssured, pytest + requests, ...).

| # | Challenge | Difficulty | Hint |
|---|---|---|---|
| A1 | **Press pay twice** | ⭐ | Real payment apps retry when the network blips. The API asks for an `Idempotency-Key` header. Does it do anything with it? |
| A2 | **Mind the paise** | ⭐⭐ | Find an account with paise in its balance. How much more than its balance can it send? |
| A3 | **Signs of trouble** | ⭐ | Think about every amount a user could type, not just the friendly ones. Boundary-value analysis is your friend. |
| A4 | **Refund, refund** | ⭐ | Refund a transfer. Then think like a customer who wants their money back again. |
| A5 | **Follow the money** | ⭐⭐ | A refund returns `201` and looks fine. Now check *both* accounts' balances, or better, the `ledger_entries` table. The three ledger rules in the main README are your test oracle. |
| A6 | **Read the contract** | ⭐⭐ | The API docs say money is always a string with two decimals. Check that every response keeps that promise, field by field. Contract tests (Pact, JSON schema) catch this kind of thing. |
| A7 | **Rush hour** | ⭐⭐⭐ | One request at a time, everything adds up. Send 20 transfers from the same account **at the same time** (threads, k6, JMeter, `xargs -P`). Is the balance exactly what it should be? Does it still match the ledger? |

## Net banking web app (port 4173): 9 bugs

Log in as `AB10001` / `Arya@2026`. Playwright, Selenium or Cypress all work, and so do your own eyes.

| # | Challenge | Difficulty | Hint |
|---|---|---|---|
| W1 | **What's this button?** | ⭐⭐ | Go through Send money to the review step with a screen reader, or run axe-core / Lighthouse on that step. |
| W2 | **Can you read it?** | ⭐⭐ | Get the login wrong on purpose and look at the message. WCAG 2.2 has a number for this. |
| W3 | **The amount you meant** | ⭐ | Send an amount with paise. Compare what you typed, what the review shows, and what the statement says. |
| W4 | **Small screens** | ⭐⭐ | Use a phone-sized viewport (under 600 px wide). Can you still reach everything without scrolling sideways? |
| W5 | **Impatient thumbs** | ⭐⭐ | On the review step, what happens if Confirm is clicked more than once, quickly? Check the statement afterwards. |
| W6 | **Bad news, good face** | ⭐⭐⭐ | Make the transfer API fail (block it in DevTools, or mock it with `page.route` in Playwright). What does the customer see? |
| W7 | **Nameless fields** | ⭐⭐ | Open the add-beneficiary form with a screen reader or an accessibility checker. |
| W8 | **Are you really out?** | ⭐⭐ | Log out. Then press Back, or open `/dashboard` directly. |
| W9 | **Works on my browser** | ⭐⭐⭐ | Open the statement page in Firefox or Safari (Playwright's `firefox` / `webkit`), not just Chrome. |

---

## Scoring yourself

- **Found it**: you can describe the wrong behaviour and the expected behaviour.
- **Proved it**: you have exact steps, and clean mode behaves correctly with the same steps.
- **Automated it**: a test that fails in practice mode and passes in clean mode. This is the real goal:
  it's what a regression suite is for.

Found something that's *not* in this list? It might be a real bug. Please
[open an issue](https://github.com/byshivam/arya-bank-sandbox/issues/new/choose).

Want to share your solutions? Post a link to your test repo in
[Discussions](https://github.com/byshivam/arya-bank-sandbox/discussions). Please don't paste
answers into issues, so others can still play.
