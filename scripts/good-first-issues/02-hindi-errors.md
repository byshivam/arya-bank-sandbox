title: Hindi error messages with Accept-Language: hi
labels: good first issue, enhancement, payments-api
---
When a request has `Accept-Language: hi`, return error `message`s in Hindi (the `code` stays the same, e.g. `INSUFFICIENT_FUNDS`).

**Done when**
- A small message table for every error code in `arya_payments/main.py`
- English stays the default
- A test that checks one Hindi message and that codes do not change

Native Hindi speakers especially welcome to review.
