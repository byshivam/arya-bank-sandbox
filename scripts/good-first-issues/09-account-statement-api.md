title: Filter API transactions by date and direction
labels: good first issue, enhancement, payments-api
---
Add optional `from`, `to` (YYYY-MM-DD) and `direction` (DEBIT/CREDIT) query parameters to `GET /accounts/{id}/transactions`, with `422` for bad values. Add tests and update the README table.
