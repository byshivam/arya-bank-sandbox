# Changelog

New planted bugs and challenges ship in monthly releases. Each release is a Docker image tag,
so test suites can pin a version and upgrade on purpose.

## [1.0.0] - 2026-10-08

First public release.

- Payments API (FastAPI + SQLite): accounts, UPI-style transfers with idempotency keys, refunds,
  double-entry ledger, Swagger docs at `/docs`
- Net banking web app (Node): login with lockout, dashboard, send money, beneficiaries, statements
- 16 planted bugs: 7 in the API (BUG-01..07), 9 in the web app (UI-01..09)
- Practice mode (all bugs on) and clean mode (none), set with `ARYA_MODE`
- Synthetic seed data with Faker: 25 customers, 60 transfers, 4 refunds, same on every machine
- Reset endpoints: `POST /_admin/reset` (API) and `POST /api/_admin/reset` (web)
- One Docker image for both apps (amd64 + arm64), Codespaces dev container
- Challenges with hints, answers in a separate file
