title: "Reset sandbox" link in the web app footer
labels: good first issue, netbanking-web
---
Learners often want a fresh start without curl. Add a small "Reset sandbox data" link in the footer of every page that calls `POST /api/_admin/reset`, shows a confirmation, and returns to the login page. Hide it when `ARYA_ADMIN=0`.
