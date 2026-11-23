# Budget Compass: ten-minute demo

## Prepare once

Use the verified public URL after Render deployment. Open the GitHub repository and [passing workflow](https://github.com/gerald-evans-j/budget-compass/actions/runs/45291728508) in separate tabs. Keep a fresh test account ready. Choose **Try the demo**, select October 2026, and download its sample CSV. This version contains nine October transactions. Use a new account or an empty month so earlier entries do not affect the expected totals.

## Demonstration

| Time | Action | Suggested explanation |
| --- | --- | --- |
| 0:00-1:00 | Open the landing page and explain the problem. | "Budget Compass helps students track part-time income and everyday expenses in one place. Maya, my example user, needs quick entry, a monthly balance, and a CSV backup." |
| 1:00-2:00 | Show the report's architecture diagram. | "The browser uses Flask routes and templates. SQLAlchemy stores users and transactions. SQLite supports local development, and PostgreSQL supports the cloud design. Gunicorn serves the application inside Docker." |
| 2:00-3:00 | Register or sign in; add $250 income called Campus work on 2026-11-23. | "Each account has its own entries. The password is stored as a hash, and private routes check ownership." |
| 3:00-4:00 | Add a $12.50 Food expense called Lunch; filter to November. | "Income is $250, expenses are $12.50, and the balance is $237.50. The app stores amounts as cents to keep calculations exact." |
| 4:00-5:00 | Filter to Food, change sort, and edit Lunch to $15.25. | "The category filter changes the list. The month still controls the overview. Editing the expense changes November's balance to $234.75." |
| 5:00-6:00 | Delete the lunch entry and confirm. | "Deletion checks that this transaction belongs to this account. Expenses return to zero and the balance returns to $250." |
| 6:00-7:00 | Import the October demo CSV; select 2026-10. | "The app validates every row before saving. October now shows $1,250 income, $689.53 expenses, and a $560.47 balance." |
| 7:00-7:30 | Download October CSV. Optionally demonstrate one invalid row in a copy. | "CSV export contains this account's selected month. An invalid import rejects the whole file and identifies the row." |
| 7:30-8:30 | Open /api/summary?month=2026-10 in the signed-in browser. | "The JSON endpoint returns the same totals as integer cents: 125000 income, 68953 expenses, and 56047 balance." |
| 8:30-9:30 | Show GitHub history and the passing checks. | "The project has 24 functional tests, a real Docker image build and running-container check, and an integration check against PostgreSQL." |
| 9:30-10:00 | Explain one defect and one lesson; sign out. | "A clean install exposed a missing database folder. I added folder creation and a regression test. Testing the startup path and the deployed system matters alongside testing individual features." |

## If asked about limitations

Transactions are entered manually. This version has no bank connection, password recovery, shared accounts, or automatic CSV deduplication. Re-importing the same file creates duplicate records. The initial schema is created at startup; future schema changes need migrations. Render's selected free PostgreSQL plan expires after 30 days, so confirm service availability for the evaluation date.

## Before submission

The app, report content, local checks, Docker checks, and PostgreSQL checks are prepared. The remaining requirement is an actual public deployment. Verify the assigned Render URL, run the live workflow, and update `docs/verification.json` and the report before submitting. Do not describe a prepared Blueprint as a verified deployment.
