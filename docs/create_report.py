"""Build the assignment PDF from the implementation and docs/verification.json.

Install reportlab separately, then run:
    python docs/create_report.py [output.pdf]
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
RED = colors.HexColor('#aa2935')
INK = colors.HexColor('#192027')
MUTED = colors.HexColor('#637079')
PALE = colors.HexColor('#f9e8e9')
LINE = colors.HexColor('#e7e5e1')
WHITE = colors.white
STYLES = {
    'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=31, leading=35,
                            textColor=INK, spaceAfter=10),
    'deck': ParagraphStyle('deck', fontSize=12, leading=17, textColor=MUTED, spaceAfter=13),
    'kicker': ParagraphStyle('kicker', fontName='Helvetica-Bold', fontSize=8, leading=11,
                             textColor=RED, spaceAfter=6),
    'h1': ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=18, leading=23,
                         textColor=INK, spaceAfter=12),
    'h2': ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=11, leading=14,
                         textColor=INK, spaceBefore=11, spaceAfter=6),
    'body': ParagraphStyle('body', fontSize=9.2, leading=13.2, textColor=INK, spaceAfter=8),
    'small': ParagraphStyle('small', fontSize=8.1, leading=11.3, textColor=INK, spaceAfter=5),
    'cell': ParagraphStyle('cell', fontSize=8.1, leading=11.1, textColor=INK),
    'head': ParagraphStyle('head', fontName='Helvetica-Bold', fontSize=8, leading=11,
                           textColor=WHITE),
    'code': ParagraphStyle('code', fontName='Courier', fontSize=7.7, leading=11,
                           textColor=INK, spaceAfter=9),
}


def p(text, style='body'):
    return Paragraph(text, STYLES[style])


def link(url, label=None):
    return f'<link href="{escape(url)}" color="#aa2935">{escape(label or url)}</link>'


def table(rows, widths, header=True):
    data = [[p(str(cell), 'head' if index == 0 and header else 'cell') for cell in row]
            for index, row in enumerate(rows)]
    result = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    commands = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 9),
                ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LINEBELOW', (0, 0), (-1, -1), .4, LINE)]
    if header:
        commands += [('BACKGROUND', (0, 0), (-1, 0), INK),
                     ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#faf9f7')])]
    result.setStyle(TableStyle(commands))
    return result


def callout(text):
    result = Table([[p(text)]], colWidths=[516])
    result.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PALE),
        ('LINEBEFORE', (0, 0), (0, -1), 3, RED),
        ('LEFTPADDING', (0, 0), (-1, -1), 13), ('RIGHTPADDING', (0, 0), (-1, -1), 13),
        ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return result


def heading(number, title):
    return [p(f'{number} / INDIVIDUAL PROJECT', 'kicker'), p(title, 'h1')]


def architecture():
    d = Drawing(516, 220)
    def box(x, y, w, h, title, lines, fill=WHITE):
        d.add(Rect(x, y, w, h, rx=8, ry=8, fillColor=fill, strokeColor=LINE))
        d.add(String(x+12, y+h-20, title, fontName='Helvetica-Bold', fontSize=10, fillColor=INK))
        for index, line in enumerate(lines):
            d.add(String(x+12, y+h-36-index*12, line, fontName='Helvetica', fontSize=8, fillColor=MUTED))
    def arrow(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=RED, strokeWidth=1.4))
        if y1 != y2:
            d.add(Line(x2-3, y2+5, x2, y2, strokeColor=RED, strokeWidth=1.4))
            d.add(Line(x2+3, y2+5, x2, y2, strokeColor=RED, strokeWidth=1.4))
    box(143, 163, 230, 54, 'Browser', ['HTML/CSS/JS; forms, filters, CSV, JSON'])
    arrow(258, 163, 258, 143)
    d.add(String(270, 149, 'HTTPS in the planned deployment', fontSize=7, fillColor=MUTED))
    box(25, 68, 466, 75, 'Docker container: Gunicorn + Flask', [
        'Routes and Jinja templates; signed sessions; CSRF and input validation',
        'Ownership checks on every private transaction request; summary calculation',
        'SQLAlchemy models: User and Transaction'])
    arrow(145, 68, 145, 49)
    arrow(377, 68, 377, 49)
    box(25, 0, 232, 49, 'SQLite', ['Local development; named volume in Docker'])
    box(269, 0, 222, 49, 'PostgreSQL', ['Tested in CI; planned Render database'])
    return d


def data_model():
    d = Drawing(516, 88)
    for x, width, title, lines in [(0, 190, 'User', ['id (PK), email (unique)', 'password_hash']),
        (241, 275, 'Transaction', ['id (PK), user_id (FK), kind, name, category',
                                  'amount_cents, occurred_on, created_at'])]:
        d.add(Rect(x, 2, width, 78, rx=7, ry=7, fillColor=WHITE, strokeColor=LINE))
        d.add(String(x+11, 59, title, fontName='Helvetica-Bold', fontSize=10, fillColor=INK))
        for index, line in enumerate(lines):
            d.add(String(x+11, 40-index*13, line, fontSize=8, fillColor=MUTED))
    d.add(Line(190, 43, 241, 43, strokeColor=RED, strokeWidth=1.4))
    d.add(String(197, 54, '1 : many', fontSize=7, fillColor=RED))
    return d


def decorate(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(RED)
    canvas.rect(0, height-7, width, 7, stroke=0, fill=1)
    canvas.setStrokeColor(LINE)
    canvas.line(48, 48, width-48, 48)
    canvas.setFont('Helvetica', 7.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(48, 34, 'Budget Compass | Gerald Evans | 23 November 2026')
    canvas.drawRightString(width-48, 34, str(doc.page))
    canvas.restoreState()


def build(destination):
    evidence = json.loads((ROOT/'docs/verification.json').read_text())
    public_url = evidence.get('public_url')
    deployed = bool(public_url and evidence.get('public_deployment_verified'))
    ci = evidence.get('ci', {})
    status = 'Application tested; public deployment verified.' if deployed else 'Application tested; public deployment pending.'
    repository = 'https://github.com/gerald-evans-j/budget-compass'
    branch = repository + '/tree/codex/complete-individual-project'
    doc = SimpleDocTemplate(str(destination), pagesize=letter, leftMargin=48,
        rightMargin=48, topMargin=43, bottomMargin=63,
        title='Budget Compass - Individual Project Report', author='Gerald Evans')
    s = [Spacer(1, 15), p('WINSTON-SALEM STATE UNIVERSITY', 'kicker'),
         p('Budget Compass', 'title'),
         p('Individual software engineering project report', 'deck'),
         p('<b>Gerald Evans</b> | 23 November 2026'),
         HRFlowable(width='100%', thickness=1, color=LINE), Spacer(1, 12),
         callout('<b>Status:</b> ' + status), Spacer(1, 9),
         p('<b>GitHub repository:</b> ' + link(repository), 'small'),
         p('<b>Completed work:</b> ' + link(branch, 'codex/complete-individual-project (review branch)'), 'small'),
         p('<b>Public product URL:</b> ' + (link(public_url) if deployed else 'Awaiting Render sign-in, deployment, and verification.'), 'small'),
         p('Introduction and opportunity', 'h2'),
         p('Budget Compass helps students record income and expenses, review their monthly balance, and see which categories account for their spending. A student with a part-time job may receive income at different times while making small purchases throughout the week. Scattered notes and manually updated spreadsheets can make the remaining balance difficult to check. This project brings those records into a simple account-based web application.'),
         p('Moore\'s product vision', 'h2'),
         callout('<b>FOR</b> students managing irregular income and everyday expenses, <b>WHO</b> need a quick, understandable view of their money, <b>THE</b> Budget Compass <b>IS A</b> cloud-based budget tracking web application <b>THAT</b> records transactions and shows balances and category totals. <b>UNLIKE</b> scattered notes or a manually maintained spreadsheet, <b>OUR PRODUCT</b> keeps each student\'s entries in an account and recalculates summaries as entries change.'),
         p('Persona: Maya Johnson', 'h2'),
         p('Maya is a fictional 19-year-old college student with a part-time job. She pays for food, transportation, and course materials, and often checks her budget on her phone between classes. Her goals are to record a purchase quickly, review one month at a time, correct mistakes, and download a CSV backup. Her main frustration is having to combine information from several places.'),
         p('Scope: manual transaction tracking in U.S. dollars, using sample data for the class demonstration. Bank connections, payments, multi-currency conversion, password recovery, and shared accounts are outside this version.', 'small'),
         PageBreak()]

    s += heading('02', 'Scenarios and user stories')
    scenarios = [
        ('A / Record and correct spending', 'Maya signs in and records a Food expense named Lunch for $12.50 on 23 November 2026. The entry appears and the expense total rises by $12.50. If she entered the wrong amount, she opens Edit, changes it to $15.25, and checks the updated balance.'),
        ('B / Review a month and keep a copy', 'At the end of October, Maya selects 2026-10 and reviews income, expenses, balance, and category totals. She filters the list to Food and sorts by amount. Download CSV exports all of her October transactions; the category filter only changes the displayed list.'),
        ('C / Import earlier records', 'Maya uploads a CSV with date, type, name, category, and amount columns. The app validates the complete file before saving. If one row has an invalid amount or date, it reports the row and saves nothing. She corrects the file and imports it again.')]
    for title, text in scenarios:
        s += [p(title, 'h2'), p(text, 'small')]
    s += [Spacer(1, 7), table([
        ('ID', 'User story', 'Acceptance criterion'),
        ('US1', 'As a student, I want to register and sign in so I can keep a personal budget.', 'A password hash is stored; valid credentials open the dashboard.'),
        ('US2', 'As a student, I want to add income and expenses so I can record money activity.', 'A valid transaction appears and updates totals; invalid input is rejected.'),
        ('US3', 'As a student, I want automatic totals so I can see my remaining balance.', 'Income minus expenses equals balance; values are exact integer cents.'),
        ('US4', 'As a student, I want month/category filters and sorting so I can review spending.', 'Month changes summaries and entries; category narrows the list; order changes correctly.'),
        ('US5', 'As a student, I want to edit and delete entries so I can correct mistakes.', 'Only the owner can change an entry; totals reflect the result.'),
        ('US6', 'As a student, I want to import CSV data so I can bring in earlier records.', 'Valid rows import together; any invalid row cancels the entire import.'),
        ('US7', 'As a student, I want a CSV download so I can keep a portable backup.', 'Export contains only my records, optionally limited to one month.'),
        ('US8', 'As a student, I want separate account data so other users cannot access my budget.', 'Other users cannot view, edit, delete, export, or summarize my transactions.'),
    ], [35, 255, 226]), PageBreak()]

    s += heading('03', 'Software architecture and data design')
    s += [architecture(), Spacer(1, 12),
          p('The browser receives server-rendered pages from Flask. Form submissions pass through authentication, CSRF checks, transaction validation, and ownership checks. SQLAlchemy maps the two models to the database. Gunicorn is the production application server and runs as a non-root user in the Docker image.'),
          p('Database relationship', 'h2'), data_model(), Spacer(1, 8),
          table([
              ('Data rule', 'Implementation'),
              ('Identity and ownership', 'User.email is unique. Transaction.user_id references User.id. Private queries are scoped to the signed-in user.'),
              ('Amounts and dates', 'amount_cents is an integer. kind determines income or expense. occurred_on is a calendar date; input must use YYYY-MM-DD.'),
              ('Categories and history', 'Income uses Income. Expenses use Food, Housing, Transportation, School, Entertainment, Health, or Other. created_at records creation time.'),
              ('Persistence', 'SQLite uses instance/budget.db locally. Docker uses a named volume. The Render Blueprint connects the web service to a separate PostgreSQL database.'),
          ], [132, 384]),
          p('The initial application creates its tables at startup. Schema migration tooling, pagination for very large histories, and database backup automation are future improvements.', 'small'), PageBreak()]

    s += heading('04', 'Application behavior and API design')
    s += [table([
        ('Method and route', 'Purpose and access'),
        ('GET /', 'Public introduction and a sample budget preview.'),
        ('GET /demo; /demo/export.csv', 'Public sample-only dashboard and CSV download; never returns account data.'),
        ('GET/POST /register; /login', 'Create an account or sign in. POST requires a valid form token.'),
        ('POST /logout', 'Clear the signed-in session; requires a form token.'),
        ('GET /dashboard', 'Private transaction list, totals, category breakdown, month filter, and sort controls.'),
        ('POST /transactions', 'Validate and create a transaction owned by the current user.'),
        ('GET/POST /transactions/&lt;id&gt;/edit', 'Show or update an owned entry. POST requires a form token.'),
        ('POST /transactions/&lt;id&gt;/delete', 'Delete an owned entry; requires a form token.'),
        ('POST /transactions/import', 'Validate and atomically import a UTF-8 CSV with no more than 500 rows and a 1 MB request limit.'),
        ('GET /transactions/export.csv', 'Download the current user\'s records, optionally limited by month.'),
        ('GET /api/summary?month=YYYY-MM', 'Return integer-cent totals and category sums; 401 if signed out and 400 for an invalid month.'),
        ('GET /health', 'Public database reachability check for service monitoring.'),
    ], [230, 286]),
    p('Example summary response', 'h2'),
    p('With $250.00 income and a $12.50 Food expense in November, an authenticated request to /api/summary?month=2026-11 returns:', 'small'),
    callout('{"month":"2026-11", "income_cents":25000,<br/>"expenses_cents":1250, "balance_cents":23750,<br/>"by_category_cents":{"Food":1250}}'),
    p('Key behavior', 'h2'),
    p('The selected month limits the overview and transaction history. Category filters narrow only the history, keeping monthly totals visible. CSV import validates every row before committing. Export prefixes formula-like descriptions so spreadsheet applications treat them as text. The public demo reads a separate sample file and does not create users or transactions.'),
    p('Implementation', 'h2'),
    p('The source includes an application factory, SQLAlchemy models, Jinja templates, responsive CSS, and JavaScript for transaction-type controls and deletion confirmation. Flask routes own input validation and authorization. The Dockerfile installs pinned top-level dependencies, copies runtime files, creates a writable data directory, and starts Gunicorn on PORT.'), PageBreak()]

    s += heading('05', 'Testing, containerization, and deployment')
    ci_link = ci.get('run_url')
    s += [p('Verification date: <b>' + escape(evidence['verified_on']) + '</b>. Tests use fictional records and temporary databases. A passing integration test demonstrates the tested configuration; it does not establish that a public service has been deployed.'),
          table([
              ('Check', 'Recorded result'),
              ('Functional automated suite', f"{evidence['functional_tests']} of {evidence['functional_tests']} passed locally; hosted result: {escape(ci.get('functional', 'pending'))}."),
              ('Running HTTP workflow', 'Passed with local Gunicorn: health, sample demo, registration/sign-in, creation, exact totals, CSV export, edit, delete, and sign-out.'),
              ('PostgreSQL configuration', escape(ci.get('postgres', 'pending')) + ': same HTTP workflow using a dedicated CI PostgreSQL database.'),
              ('Docker build and runtime', escape(ci.get('docker', 'pending')) + ': build image, start with a named volume, exercise HTTP workflow, and verify runtime UID 10001.'),
              ('GitHub version control', 'Existing history plus focused commits for validation, first-run storage, CI readiness, and documentation. Changes are available on the review branch.'),
              ('Public cloud deployment', 'Verified at ' + link(public_url) if deployed else 'Pending Render sign-in, Blueprint deployment, and public end-to-end verification. No public URL is claimed.'),
          ], [153, 363]),
          p('Test coverage', 'h2'),
          p('The 24 functional tests cover registration and password hashing; failed and duplicate sign-ins; exact decimal arithmetic and negative balances; December/January boundaries; sorting and category filters; editing and deletion; cross-account access; atomic CSV validation; 500-row and 1 MB limits; HTML escaping; malformed form tokens; strict calendar dates; demo isolation; fresh-install storage; and persistence across application instances.'),
          p('Reproduce the checks', 'h2'),
          p('python -m unittest discover -s tests -v<br/>docker build -t budget-compass .<br/>python scripts/smoke_test.py http://127.0.0.1:8000', 'code'),
          p('Start the image with SECRET_KEY and the documented volume before running the smoke test. The README provides complete setup and container commands.', 'small'),
          p('Hosted evidence: ' + (link(ci_link, ci_link) if ci_link else 'Workflow is configured; completed results are not yet recorded.'), 'small'),
          p('Render publication plan', 'h2'),
          p('Deploy the included Blueprint from the completed work branch. It defines a Docker web service, a generated SECRET_KEY, secure cookies for HTTPS, a /health check, and DATABASE_URL from PostgreSQL. Confirm the plan shown in Render, deploy, open the actual assigned URL, and repeat the HTTP and browser workflow. Record that URL and result in docs/verification.json before generating the submission PDF.'),
          p('The Blueprint selects free services for a class demonstration. Render documents that free PostgreSQL expires after 30 days and free web services can spin down. Confirm database availability for the evaluation date and export demonstration data before expiration [2, 3].', 'small'), PageBreak()]

    s += heading('06', 'Challenges, lessons, and demonstration')
    for title, text in [
        ('Making a fresh installation work', 'A real startup check exposed a missing SQLite data directory that the temporary-database tests did not reveal. The factory now creates its instance folder, and a regression test starts with a missing folder.'),
        ('Validating untrusted form input', 'A non-ASCII form token raised an exception during comparison. Comparing encoded token bytes now returns a normal 400 response for invalid input. Calendar dates are checked for the documented format and real day/month validity.'),
        ('Keeping balances and imports correct', 'Integer cents keep additions and subtractions exact. Whole-file CSV validation prevents partial imports. Ownership checks protect the same transaction through the dashboard, API, edit, delete, and export paths.'),
        ('Distinguishing build success from usable deployment', 'The first container check reached the published port before the server was ready. The smoke test now retries transient startup connection errors. Separate checks cover the image, a running app, PostgreSQL, and the eventual public URL.'),
    ]:
        s += [p(title, 'h2'), p(text, 'small')]
    s += [p('Lessons learned', 'h2'),
          p('Test a clean installation as well as individual features. Treat each route as an authorization boundary. Use the same input rules for forms and imported files. Keep persistent cloud data outside the web container. Record results that were actually observed, and distinguish configured infrastructure from a verified live application.', 'small'),
          p('Ten-minute demo', 'h2'),
          table([
              ('Time', 'What to demonstrate'),
              ('0:00-2:00', 'Introduce the opportunity, Maya, product vision, and architecture diagram.'),
              ('2:00-4:00', 'Open the public URL, sign in, add income and an expense, and explain exact totals.'),
              ('4:00-6:00', 'Filter by month/category, sort, edit an amount, and delete a temporary entry.'),
              ('6:00-7:30', 'Import the sample CSV; show an invalid-row rejection and download a CSV.'),
              ('7:30-8:30', 'Show /api/summary and explain account ownership and sample-demo separation.'),
              ('8:30-10:00', 'Show GitHub commits and passing checks; explain Docker, PostgreSQL, challenges, and lessons.'),
          ], [90, 426]),
          Spacer(1, 8), p('References', 'h2'),
          p('[1] Individual Project. Assignment PDF supplied by the instructor (individual_project.pdf).<br/>'
            '[2] Render. Docker on Render. ' + link('https://render.com/docs/docker') + '.<br/>'
            '[3] Render. Deploy for Free. ' + link('https://render.com/docs/free') + '.<br/>'
            '[4] Render. Render Blueprints. ' + link('https://render.com/docs/infrastructure-as-code') + '.<br/>'
            'Render documentation reviewed 23 November 2026. Implementation and test results are supported by the linked repository and workflow.', 'small')]
    doc.build(s, onFirstPage=decorate, onLaterPages=decorate)


if __name__ == '__main__':
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'output/pdf/Budget_Compass_Project_Report.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    build(output)
    print(output)
