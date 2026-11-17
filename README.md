# Budget Compass

An account-based budget tracker for students. Record income and expenses, review balances and category totals, filter and sort transactions, edit or delete entries, and import or export CSV files. Built with Flask, SQLAlchemy, SQLite for local development, and PostgreSQL for cloud deployment.

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

The tests use temporary SQLite databases. They cover account login, stored password hashes, transaction creation/edit/deletion, monthly totals, filtering, CSV import/export, user isolation, input validation, CSRF checks, and health status.

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

The repository includes `render.yaml`, which describes a Docker web service and a PostgreSQL database. After pushing this source to your own GitHub repository:

1. In Render, choose **New → Blueprint** and connect the repository containing `render.yaml`.
2. Review the proposed web service and database, then apply the Blueprint.
3. Render supplies `DATABASE_URL` and generates `SECRET_KEY` from the Blueprint. `COOKIE_SECURE=true` is configured for HTTPS.
4. Open the resulting public service URL. Check `/health`, create a test account, add an expense, review `/api/summary`, download a CSV, and test sign out/sign in.
5. Record the actual GitHub and public URLs in the final report. Do not submit placeholder links.

Render's free PostgreSQL database is time limited; review [Render's current free tier limits](https://render.com/docs/free) before relying on it for a long-lived deployment. Do not enter real bank details or other sensitive financial information into a class demonstration.

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

The source and local tests are complete. A GitHub repository link, a successful Docker build on a Docker-enabled machine, and the final public deployment must be verified before the assignment's deployment requirements can be claimed as complete. The report keeps those fields open until verification.
