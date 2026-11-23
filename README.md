# Budget Compass

An account-based student budget tracker built with HTML/CSS/JavaScript, Python/Flask, SQLAlchemy, SQLite, PostgreSQL, Docker, and Gunicorn.

- [GitHub repository](https://github.com/gerald-evans-j/budget-compass)
- [Completed work branch](https://github.com/gerald-evans-j/budget-compass/tree/codex/complete-individual-project)
- [Review changes](https://github.com/gerald-evans-j/budget-compass/pull/1)
- [Passing functional, Docker, and PostgreSQL checks](https://github.com/gerald-evans-j/budget-compass/actions/runs/45291728508)
- **Public product URL:** awaiting Render sign-in, deployment, and verification.

## Features and usage

Choose **Try the demo** to explore fictional September and October transactions without an account. October contains $1,250.00 income, $689.53 expenses, and a $560.47 balance. The demo never displays a signed-in user's records.

Create an account, sign in, and add income or expenses using a description, category, amount, and date. Use **Edit** or **Delete** to correct entries. Filter by month, category, or amount/date order. The month controls the overview and list; category controls the list. **Download CSV** exports all your records in the chosen month, regardless of the category filter. **Import CSV** validates the entire file before saving.

## Run locally on macOS or Linux

Requires Python 3.12 or newer. Clone this repository, then enter its folder. The latest completed changes are on the review branch until merged:

```bash
git clone https://github.com/gerald-evans-j/budget-compass.git
cd budget-compass
git switch codex/complete-individual-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m flask --app wsgi run --port 5050
```

If you downloaded the source ZIP, extract it and open the `budget-compass` folder, then start at the virtual-environment command. Visit http://127.0.0.1:5050. The app creates `instance/budget.db` on first startup. Port 5050 avoids the common macOS port 5000 conflict. Keep SECRET_KEY stable if you want sessions to survive restarts.

## Run locally on Windows (PowerShell)

Open the extracted project folder in PowerShell, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
python -m flask --app wsgi run --port 5050
```

If activation is blocked, call `.venv\Scripts\python.exe` instead of `python` in these commands. You do not need to change your system execution policy. Visit http://127.0.0.1:5050.

## Automated verification

```bash
python -m unittest discover -s tests -v
```

**24 functional tests pass**, including exact calculations, account separation, CSV validation, month boundaries, sorting, HTML escaping, malformed form tokens, strict dates, first-run storage, and persistence. GitHub Actions also builds/runs the Docker image, checks runtime UID 10001, and exercises the HTTP workflow using PostgreSQL 16. See the linked passing run above.

To exercise a running local container or a deployed service:

```bash
python scripts/smoke_test.py http://127.0.0.1:8000
```

The smoke check creates one account with a randomized `example.test` address, adds fictional transactions, checks totals/export/edit/delete, removes those transactions, and signs out. An empty test account remains. Use it against a service you own.

## Docker

With Docker Desktop running and SECRET_KEY set in your shell:

```bash
docker build -t budget-compass .
docker volume create budget-compass-data
docker run --rm -p 8000:8000 --env SECRET_KEY -v budget-compass-data:/app/instance budget-compass
```

Visit http://localhost:8000. The named volume preserves SQLite data between container runs. The image uses Python 3.12, runs Gunicorn as non-root UID 10001, and binds to PORT (default 8000). It was built and exercised successfully in GitHub Actions. For public cloud storage, supply a PostgreSQL DATABASE_URL rather than relying on a temporary web-service filesystem.

## Deploy to Render

`render.yaml` defines a Docker web service and a PostgreSQL database on free plans. The deployment is prepared; a public URL has not yet been verified.

1. Sign in at https://dashboard.render.com and choose **New > Blueprint**.
2. Connect `gerald-evans-j/budget-compass`. Select `codex/complete-individual-project` to deploy this version, or select `main` after merging the review branch.
3. Keep the Blueprint path `render.yaml`. Review both proposed resources and confirm that their plans are free. If your workspace already has its permitted free PostgreSQL database, do not delete that database or upgrade a plan automatically; use a suitable existing database or decide on an alternative.
4. Deploy. The Blueprint generates SECRET_KEY, sets COOKIE_SECURE=true, and injects the PostgreSQL connection as DATABASE_URL.
5. Open the actual URL assigned by Render. Check `/health`, `/demo`, registration, sign-in, add/edit/delete, CSV import/export, and `/api/summary?month=2026-10`.
6. Record the real URL and the observed result in `docs/verification.json`; regenerate the report. Do not mark `public_deployment_verified` true until the public app has been checked.

Render documents that free web services can spin down and free PostgreSQL databases expire after 30 days. Confirm availability for the evaluation date. See [Docker hosting](https://render.com/docs/docker), [Blueprints](https://render.com/docs/infrastructure-as-code), and [free-tier limits](https://render.com/docs/free).

## CSV format

Headers must be exactly:

```csv
date,type,name,category,amount
```

Example:

```csv
2026-11-23,income,Campus work,Income,250.00
2026-11-23,expense,Lunch,Food,12.50
```

Use a real date in `YYYY-MM-DD` format. Types are `income` or `expense`. Income uses the `Income` category. Expense categories: Food, Housing, Transportation, School, Entertainment, Health, Other. Amounts must be positive, at most 9,999,999.99, and use no more than two decimal places.

Import accepts UTF-8 (with or without BOM), up to 500 rows, and a maximum request size of 1 MB. Any invalid row cancels the whole import. Export prefixes spreadsheet formula markers with an apostrophe; these names remain text when opened in a spreadsheet. `sample_transactions.csv` contains both sample months. Importing the same file twice creates duplicate transactions; automatic deduplication is outside this version.

## Configuration

| Setting | Purpose |
| --- | --- |
| SECRET_KEY | Required; protects signed sessions and form tokens. Generated by the Render Blueprint. |
| DATABASE_URL | Defaults to local SQLite; set a PostgreSQL connection for persistent cloud data. PostgreSQL URLs are normalized for psycopg 3. |
| COOKIE_SECURE | Set to `true` for HTTPS. Keep false/unset for local HTTP. |
| PORT | Gunicorn listening port in Docker; defaults to 8000. |

`GET /health` checks database access. Authenticated `GET /api/summary?month=YYYY-MM` returns income, expenses, balance, and category totals as integer cents. Signed-out calls return HTTP 401; invalid months return 400. Private transaction paths enforce ownership and POST changes require a valid CSRF form token.

## Assignment documentation

- `docs/PROJECT_SPEC.md`: opportunity, Moore vision, persona, three scenarios, eight stories, architecture, schema, and routes.
- `docs/DEMO_GUIDE.md`: ten-minute walkthrough and expected sample totals.
- `docs/verification.json`: observed test results and deployment status.
- `docs/create_report.py`: creates the assignment report PDF. Install `reportlab`, then run `python docs/create_report.py`. Output goes to `output/pdf/Budget_Compass_Project_Report.pdf`.
- `tests/test_app.py`: 24 functional tests.
- `scripts/smoke_test.py`: HTTP checks for a running service.
- `.github/workflows/ci.yml`: functional, Docker, and PostgreSQL checks.

The separate PDF report includes the required introduction, links/status, opportunity, product vision, persona, scenarios, user stories, architecture/data/API design, challenges, and lessons learned. Its public URL section remains pending until deployment is verified.

## Current limitations

This version uses manual entries, a single currency, and account-specific data. Password recovery, email verification, sign-in rate limiting, database migrations, pagination, bank integration, and automatic CSV deduplication are future work. Public evaluation should use the prepared sample data.
