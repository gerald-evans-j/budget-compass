"""Regenerate the project report with: python docs/create_report.py docs/Budget_Compass_Project_Report.pdf"""

import sys
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)


RED = colors.HexColor("#aa2935")
INK = colors.HexColor("#192027")
MUTED = colors.HexColor("#637079")
PALE = colors.HexColor("#f9e8e9")
LINE = colors.HexColor("#e7e5e1")
WHITE = colors.white


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=29,
                          leading=34, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name="Kicker", fontName="Helvetica-Bold", fontSize=8.5,
                          leading=12, textColor=RED, spaceAfter=7))
styles.add(ParagraphStyle(name="Deck", fontName="Helvetica", fontSize=12,
                          leading=18, textColor=MUTED, spaceAfter=18))
styles.add(ParagraphStyle(name="SectionCustom", fontName="Helvetica-Bold", fontSize=15,
                          leading=19, textColor=INK, spaceBefore=19, spaceAfter=8))
styles.add(ParagraphStyle(name="SubCustom", fontName="Helvetica-Bold", fontSize=10.5,
                          leading=14, textColor=INK, spaceBefore=10, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyCustom", fontName="Helvetica", fontSize=9.2,
                          leading=14, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle(name="SmallCustom", fontName="Helvetica", fontSize=8,
                          leading=11.5, textColor=INK))
styles.add(ParagraphStyle(name="TinyCustom", fontName="Helvetica", fontSize=7.7,
                          leading=10.5, textColor=INK))
styles.add(ParagraphStyle(name="TableHead", fontName="Helvetica-Bold", fontSize=8,
                          leading=11, textColor=WHITE))
styles.add(ParagraphStyle(name="Status", fontName="Helvetica-Bold", fontSize=8,
                          leading=11, textColor=RED))


def p(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def section(label, title):
    return [p(label.upper(), "Kicker"), p(title, "SectionCustom")]


def table(rows, widths, *, header=True):
    content = []
    for i, row in enumerate(rows):
        content.append([p(cell, "TableHead" if i == 0 and header else "TinyCustom")
                        for cell in row])
    t = Table(content, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("LINEBELOW", (0, 0), (-1, -1), .4, LINE)]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), INK),
                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#faf9f7")])]
    t.setStyle(TableStyle(commands))
    return t


def architecture():
    d = Drawing(515, 144)
    nodes = [(8, "Browser", "HTML / CSS / JS"), (182, "Flask", "Routes / auth / validation"),
             (356, "Database", "SQLite / PostgreSQL")]
    for x, title, detail in nodes:
        d.add(Rect(x, 45, 151, 77, rx=9, ry=9, fillColor=WHITE, strokeColor=LINE,
                   strokeWidth=1.4))
        d.add(Rect(x, 113, 151, 9, fillColor=RED, strokeColor=RED))
        d.add(String(x + 13, 87, title, fontName="Helvetica-Bold", fontSize=12, fillColor=INK))
        d.add(String(x + 13, 64, detail, fontName="Helvetica", fontSize=8, fillColor=MUTED))
    for start, end in [(159, 182), (333, 356)]:
        d.add(Line(start + 2, 82, end - 5, 82, strokeColor=RED, strokeWidth=2))
        d.add(Line(end - 11, 87, end - 5, 82, strokeColor=RED, strokeWidth=2))
        d.add(Line(end - 11, 77, end - 5, 82, strokeColor=RED, strokeWidth=2))
    d.add(String(8, 13, "HTTPS forms + summary API", fontName="Helvetica", fontSize=8, fillColor=MUTED))
    d.add(String(357, 13, "SQLAlchemy models", fontName="Helvetica", fontSize=8, fillColor=MUTED))
    return d


def decorate(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(RED)
    canvas.rect(0, height - 8, width, 8, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.line(48, 49, width - 48, 49)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(48, 35, "Budget Compass | Individual project report | 23 September 2026")
    canvas.drawRightString(width - 48, 35, str(doc.page))
    canvas.restoreState()


def build(destination):
    doc = SimpleDocTemplate(str(destination), pagesize=letter, leftMargin=48,
                            rightMargin=48, topMargin=45, bottomMargin=64,
                            title="Budget Compass - Individual Project Report",
                            author="Gerald Evans")
    story = []

    # Page 1: summary and definition
    story += [Spacer(1, 25), p("INDIVIDUAL SOFTWARE ENGINEERING PROJECT", "Kicker"),
              p("Budget Compass", "CoverTitle"),
              p("A student budget tracker with account-based transactions, monthly summaries, and CSV portability.", "Deck"),
              HRFlowable(width="100%", thickness=1, color=LINE), Spacer(1, 14)]
    story += [p("Prepared by <b>Gerald Evans</b> | Winston-Salem State University", "BodyCustom"),
              p("<b>Project status:</b> Application implemented and locally tested. GitHub publication, Docker image testing, and cloud deployment still require verification.", "BodyCustom")]
    story += section("01 / introduction", "The opportunity")
    story.append(p("Students with irregular income and everyday expenses may scatter entries across notes or spreadsheets. Budget Compass gives them one place to record activity and see the balance and spending categories update automatically. This is an educational tracker; it does not process payments or connect to banks."))
    story += section("02 / product vision", "Moore's product vision")
    vision = "<b>FOR</b> students who manage irregular income and everyday expenses, <b>WHO</b> need a quick, understandable view of their money, <b>THE</b> Budget Compass <b>IS A</b> cloud-based budget tracking web app <b>THAT</b> records transactions and shows balances and spending by category. <b>UNLIKE</b> scattered notes or a manually maintained spreadsheet, <b>OUR PRODUCT</b> keeps each student's entries in an account and updates summaries when entries change."
    v = Table([[p(vision)]], colWidths=[516]); v.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), .7, RED), ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16), ("TOPPADDING", (0, 0), (-1, -1), 15),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9)])); story.append(v)
    story += section("03 / persona", "Maya Johnson")
    story.append(p("Maya is a fictional 19-year-old student with a part-time job. Her income arrives at irregular intervals, and she pays for food, transportation, and school materials. She checks her budget on a phone between classes. She needs quick entry, a monthly view, and a CSV backup."))
    story.append(PageBreak())

    # Page 2: scenarios and user stories
    story += section("04 / scenarios", "Key interactions")
    story.append(table([
        ("Scenario", "User interaction and outcome"),
        ("A | Record spending", "Maya signs in, adds a $12.50 Food expense, sees her balance update, then edits the amount if she made a mistake."),
        ("B | Review a month", "Maya selects a month, reviews totals by category, filters the list to Food, and downloads only her own entries for that month."),
        ("C | Import history", "Maya uploads a CSV. Every row is validated before saving. If one row is invalid, the app reports it and imports nothing."),
    ], [130, 386]))
    story += section("05 / user stories", "Eight planned features")
    story.append(table([
        ("ID", "As a student, I want to...", "Done when..."),
        ("US1", "Create an account and sign in", "A password hash is stored; valid sign-in opens the dashboard."),
        ("US2", "Add income and expenses", "A valid entry appears and changes totals."),
        ("US3", "See income, expenses, and balance", "Dashboard and API totals match stored entries."),
        ("US4", "Filter by month/category and sort", "Selected views show the expected entries and totals."),
        ("US5", "Edit or delete an entry", "Changes update totals; ownership is checked."),
        ("US6", "Import a CSV", "All valid rows import together; a bad row cancels import."),
        ("US7", "Download a CSV", "The file contains only my entries, optionally one month."),
        ("US8", "Keep my data separate", "Other accounts cannot read or modify my entries."),
    ], [37, 218, 261]))
    story.append(PageBreak())

    # Page 3: architecture
    story += section("06 / architecture", "How the product works")
    story.append(architecture())
    story.append(p("The browser submits forms and requests pages over HTTPS. Flask checks the signed-in session and form token, validates inputs, and reads or changes only the current user's records. SQLAlchemy writes to SQLite during local development and PostgreSQL when the app is deployed. Gunicorn serves Flask inside the Docker container."))
    story.append(p("<b>Money representation:</b> Positive transaction amounts are stored as integer cents. Balance = total income - total expenses. The selected month limits both totals and the transaction list; a category filter narrows only the list."))
    story.append(p("<b>Data design:</b> A User has a unique email and a password hash. One User owns many Transactions. Each Transaction has a user ID, kind (income/expense), description, category, amount in cents, date, and creation time."))
    story += section("07 / routes", "API and interface")
    story.append(table([
        ("Route", "What it does"),
        ("/register, /login, /logout", "Account access, with session and form protections."),
        ("/dashboard", "Transaction list, month/category filters, and totals."),
        ("/transactions (+ edit, delete)", "Create or change only the signed-in user's entries."),
        ("/transactions/import, /export.csv", "Validate and import CSV; download an account-specific CSV."),
        ("GET /api/summary?month=YYYY-MM", "Return income_cents, expenses_cents, balance_cents, and category totals as JSON."),
        ("GET /health", "Check the database connection for deployment monitoring."),
    ], [210, 306]))
    story.append(PageBreak())

    # Page 4: evidence, reflection, delivery
    story += section("08 / implementation and test", "What is complete")
    story.append(p("The repository contains the Flask application, responsive templates, database models, CSV import/export, tests, Dockerfile, Render Blueprint, and README. Three local Git commits separate the implementation, test/deployment setup, and documentation. The initial automated run passed 6 of 6 functional tests."))
    story.append(table([
        ("Check", "Result"),
        ("Local functional tests", "6 passed: account flow, calculations, edits, filters, CSV, privacy, validation, CSRF, health."),
        ("Docker image build and run", "Pending a machine with Docker; image not yet verified."),
        ("GitHub repository", "Pending connection/publication. Add the actual link after pushing."),
        ("Cloud deploy and public URL", "Pending Render deployment and end-to-end browser check."),
    ], [185, 331]))
    story += section("09 / challenges and lessons", "Engineering decisions")
    story.append(p("The earlier static tracker supplied the idea, but account-based storage required a new server design. Every transaction query and edit must check user ownership. Integer cents avoid floating-point rounding in balances. CSV rows are validated before any are committed so a bad file cannot leave partial data. PostgreSQL is needed on the cloud service because the web container's filesystem is temporary."))
    story += section("10 / submission and demonstration", "Finish the deployment evidence")
    story.append(p("<b>GitHub repository:</b> Pending - insert the verified repository URL.<br/><b>Public product URL:</b> Pending - insert the verified deployed URL.<br/><b>Deployment check:</b> After deployment, test /health, registration, sign-in, add/edit/delete, summary, CSV export/import, and sign-out on the live site."))
    story.append(p("<b>Ten-minute demo:</b> 0-2 min vision and architecture; 2-5 min sign in and add transactions; 5-7 min filter, edit, delete, and CSV; 7-8 min JSON summary and account separation; 8-10 min tests, Dockerfile, GitHub history, public URL, challenges, and lessons."))
    story.append(p("<b>Sources:</b> Project instructions supplied for this assignment; Render documentation for Docker/Blueprint deployment and temporary web-service storage: https://render.com/docs/blueprint-spec and https://render.com/docs/free.", "SmallCustom"))

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/Budget_Compass_Project_Report.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    build(output)
