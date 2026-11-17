# Budget Compass

An account-based budget tracker for students. Record income and expenses, review balances and category totals, filter and sort transactions, edit or delete entries, and import or export CSV files. Built with Flask, SQLAlchemy, SQLite for local development, and PostgreSQL for cloud deployment.

## Try the demo

Choose **Try the demo** on the home page to explore September and October sample budgets without an account. October starts with $1,250.00 in income, $689.53 in expenses, and a $560.47 balance. Change the month or filter by category, then choose **Download CSV** to export that month.

To try the full workflow, create a test account and import the downloaded CSV. The import panel also offers a sample file containing both months. Review the totals, edit a transaction, and export the updated budget.

## Run locally

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
flask --app wsgi run
```

Visit http://127.0.0.1:5000, create an account, and add a transaction. Local data is created in `instance/budget.db`. Keep `SECRET_KEY` stable across restarts if you want existing sessions to remain signed in. On Windows, use `.venv\Scripts\activate` and `set SECRET_KEY=...` in Command Prompt or `$env:SECRET_KEY="..."` in PowerShell.

## Automated tests

```bash
python -m unittest discover -s tests -v
```

The tests use temporary SQLite databases. They cover sign-in, account isolation, transaction editing, monthly totals, filters, CSV validation and export, and the public demo's sample-only data.

## Docker

```bash
docker build -t budget-compass .
docker volume create budget-compass-data
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  -v budget-compass-data:/app/instance budget-compass
```

Open http://localhost:8000. The named volume keeps local SQLite data between container runs. The image runs Gunicorn as a non-root user and binds to the `PORT` environment variable, defaulting to 8000. For a public deployment, configure a persistent PostgreSQL `DATABASE_URL` and a strong `SECRET_KEY`.

## Deploy to Render

The repository includes `render.yaml`, which defines a Docker web service and a PostgreSQL database. For the first publication from the source ZIP, open the extracted `budget-compass` directory and push the included commit history to the dedicated GitHub repo.

```bash
git remote add origin https://github.com/gerald-evans-j/budget-compass.git
git push -u origin main
```

Then deploy:

1. In Render, choose **New → Blueprint** and connect the repository containing `render.yaml`. See the [Render Blueprint guide](https://render.com/docs/infrastructure-as-code).
2. Review the proposed web service and database, then apply the Blueprint.
3. Render supplies `DATABASE_URL` and generates `SECRET_KEY` from the Blueprint. `COOKIE_SECURE=true` is configured for HTTPS.
4. Open the public service URL and check `/health` and `/demo`. Create a test account, import the sample CSV, and compare the dashboard totals with `/api/summary?month=2026-10`.
5. Add the verified public URL to the project README and your resume.

Render's free PostgreSQL database expires 30 days after creation. The project's Blueprint uses that plan for a short demo. See [Render's free tier limits](https://render.com/docs/free).

## CSV format

The first line must be exactly:

```csv
date,type,name,category,amount
```

Example:

```csv
2026-09-10,income,Campus job,Income,200.00
2026-09-11,expense,Lunch,Food,12.50
```

After creating a test account, import `sample_transactions.csv` or the file downloaded from the demo dashboard.

Dates use `YYYY-MM-DD`; types are `income` or `expense`. Income uses the `Income` category. Expense categories are Food, Housing, Transportation, School, Entertainment, Health, and Other. Import accepts up to 500 rows and a maximum request size of 1 MB. An invalid row cancels the whole import. Export escapes text that a spreadsheet could interpret as a formula.

## Project files

- `app.py`: application factory, validation, authentication, routes, and data models.
- `templates/`, `static/`: responsive user interface.
- `tests/test_app.py`: functional automated tests.
- `docs/PROJECT_SPEC.md`: vision, persona, scenarios, stories, architecture, and demo plan.
- `docs/Budget_Compass_Project_Report.pdf`: report draft with verified local results and clearly marked deployment fields. Regenerate it with `python docs/create_report.py docs/Budget_Compass_Project_Report.pdf` after installing `reportlab` if the live links are added to the script.
- `Dockerfile`, `render.yaml`: container and cloud configuration.

## Configuration and endpoints

| Setting | Purpose |
| --- | --- |
| `SECRET_KEY` | Required; protects sessions and form tokens. |
| `DATABASE_URL` | Optional locally (defaults to SQLite); required for persistent cloud data. Accepts PostgreSQL URLs. |
| `COOKIE_SECURE` | Set to `true` for HTTPS deployments. |
| `PORT` | Gunicorn listening port inside the container; defaults to 8000. |

`GET /health` reports the database is reachable. Authenticated `GET /api/summary?month=YYYY-MM` returns income, expenses, balance, and expense totals by category in integer cents. See `docs/PROJECT_SPEC.md` for the full route and data design.

## Project status

The app and automated tests run locally with SQLite. GitHub publication, the Docker image build, and the public Render URL are pending verification.
