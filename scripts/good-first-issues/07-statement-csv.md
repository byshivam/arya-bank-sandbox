title: Download statement as CSV in the web app
labels: good first issue, enhancement, netbanking-web
---
The statement page has a date filter. Add a "Download CSV" button that downloads the filtered transactions (`date,description,account,direction,amount`).

**Done when**
- New endpoint `GET /api/transactions.csv` with the same filters
- Amounts as `1500.75` (no currency symbol), dates as `YYYY-MM-DD`
- Works in clean mode; button has an accessible name
