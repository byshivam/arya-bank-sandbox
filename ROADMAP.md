# Roadmap

Rough plan, not a promise. Vote with 👍 on issues, or suggest things in
[Discussions](https://github.com/byshivam/arya-bank-sandbox/discussions).

## Next (v1.1, November 2026)

- **Loan EMI calculator endpoint** with rounding bugs to find
- **Hindi error messages** (`Accept-Language: hi`), and a bug where one message isn't translated
- **Postman collection** and a REST Client `.http` file for every endpoint
- **Starter test suites** in pytest + requests and in Java + RestAssured, with one test per area to copy

## Later

- Connect the net banking app to the payments API, so a UI transfer shows up in the ledger
  (end-to-end tests from browser to database)
- Fixed deposits: interest calculation, premature withdrawal penalty, date-boundary bugs
- Statement download as CSV and PDF (file content testing)
- Rate limiting on login and transfers (`429` handling)
- An OTP step on high-value transfers (with a fake SMS inbox endpoint)
- "Bug of the month": one new planted bug and challenge every release
- A leaderboard page in Discussions for people who automate all 16

## Maybe

- Host a public demo (with scheduled resets), if enough people ask for it
- GraphQL version of the payments API
- Kafka events for transfers (event-driven testing)
