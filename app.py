"""Budget Compass: a small, account-based student budget tracker."""

import csv
import hmac
import io
import os
import re
import secrets
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from operator import attrgetter
from pathlib import Path

from flask import (
    Flask, abort, flash, g, jsonify, redirect, render_template, request,
    Response, session, url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()
EXPENSE_CATEGORIES = ("Food", "Housing", "Transportation", "School", "Entertainment", "Health", "Other")
CSV_FIELDS = ("date", "type", "name", "category", "amount")
MAX_IMPORT_ROWS = 500
TRANSACTION_SORT_ORDERS = {
    "newest": ("occurred_on", True),
    "oldest": ("occurred_on", False),
    "high": ("amount_cents", True),
    "low": ("amount_cents", False),
}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    transactions = db.relationship("Transaction", backref="owner", cascade="all, delete-orphan")


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    kind = db.Column(db.String(7), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(32), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    occurred_on = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def parse_transaction(fields):
    kind = str(fields.get("type", "")).strip().lower()
    name = str(fields.get("name", "")).strip()
    category = str(fields.get("category", "")).strip()
    raw_amount = str(fields.get("amount", "")).strip()
    raw_date = str(fields.get("date", "")).strip()
    if kind not in {"income", "expense"}:
        raise ValueError("Type must be income or expense.")
    if not 1 <= len(name) <= 80:
        raise ValueError("Description must be between 1 and 80 characters.")
    if any(ord(char) < 32 for char in name):
        raise ValueError("Description cannot contain control characters.")
    allowed = {"Income"} if kind == "income" else set(EXPENSE_CATEGORIES)
    if category not in allowed:
        raise ValueError("Choose a valid category for the transaction type.")
    try:
        amount = Decimal(raw_amount)
        if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999.99"):
            raise ValueError("Amount must be greater than zero and at most 9,999,999.99.")
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError("Use no more than two decimal places for the amount.")
    except (InvalidOperation, TypeError):
        raise ValueError("Enter a valid amount.") from None
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_date):
        raise ValueError("Enter a valid date in YYYY-MM-DD format.")
    try:
        occurred_on = date.fromisoformat(raw_date)
    except ValueError:
        raise ValueError("Enter a valid date in YYYY-MM-DD format.") from None
    return dict(kind=kind, name=name, category=category,
                amount_cents=int(amount * 100), occurred_on=occurred_on)


def parse_month(value):
    if not value:
        return None
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValueError("Choose a valid month.")
    result = date.fromisoformat(value + "-01")
    if result.year >= 9999:
        raise ValueError("Choose a month before the year 9999.")
    return result


def month_query(query, month):
    if month:
        if month.month == 12:
            next_month = date(month.year + 1, 1, 1)
        else:
            next_month = date(month.year, month.month + 1, 1)
        query = query.filter(Transaction.occurred_on >= month,
                             Transaction.occurred_on < next_month)
    return query


def safe_csv_cell(value):
    # A spreadsheet must treat user text as text, even when it starts with a formula marker.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def transaction_csv(rows, filename):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_FIELDS)
    for item in rows:
        writer.writerow([item.occurred_on.isoformat(), item.kind,
                         safe_csv_cell(item.name), item.category,
                         f"{Decimal(item.amount_cents) / 100:.2f}"])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}",
                             "Cache-Control": "no-store"})


def sample_transactions():
    sample_file = Path(__file__).with_name("sample_transactions.csv")
    with sample_file.open(encoding="utf-8", newline="") as source:
        return [Transaction(**parse_transaction(row)) for row in csv.DictReader(source)]


def sample_month_transactions(rows, month):
    return [item for item in rows if month is None or item.occurred_on.replace(day=1) == month]


def summarize_transactions(rows):
    income = sum(item.amount_cents for item in rows if item.kind == "income")
    expenses = sum(item.amount_cents for item in rows if item.kind == "expense")
    categories = {
        category: sum(item.amount_cents for item in rows
                      if item.kind == "expense" and item.category == category)
        for category in EXPENSE_CATEGORIES
    }
    return {"income_cents": income, "expenses_cents": expenses,
            "balance_cents": income - expenses,
            "by_category_cents": {category: cents for category, cents in categories.items() if cents}}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def create_app(test_config=None):
    app = Flask(__name__)
    database_url = os.environ.get("DATABASE_URL", "sqlite:///budget.db")
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        MAX_CONTENT_LENGTH=1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "true",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Set SECRET_KEY to a long random value before starting the app.")
    database_schema = os.environ.get("DATABASE_SCHEMA", "")
    if database_schema:
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", database_schema):
            raise RuntimeError("DATABASE_SCHEMA must be a lowercase PostgreSQL schema name.")
        if not str(app.config["SQLALCHEMY_DATABASE_URI"]).startswith("postgresql"):
            raise RuntimeError("DATABASE_SCHEMA requires a PostgreSQL database.")
        engine_options = dict(app.config["SQLALCHEMY_ENGINE_OPTIONS"])
        engine_options["schema_translate_map"] = {None: database_schema}
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    @app.before_request
    def load_user_and_check_csrf():
        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if isinstance(user_id, int) else None
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected.encode("utf-8"), supplied.encode("utf-8")):
                abort(400, description="Form expired. Reload the page and try again.")

    @app.context_processor
    def inject_common():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"current_user": g.get("user"), "csrf_token": session["csrf_token"],
                "expense_categories": EXPENSE_CATEGORIES}

    @app.template_filter("money")
    def money(cents):
        return f"${Decimal(cents or 0) / 100:,.2f}"

    @app.get("/")
    def home():
        if g.user:
            return redirect(url_for("dashboard"))
        rows = sample_transactions()
        month = max(item.occurred_on for item in rows).replace(day=1)
        return render_template("home.html", sample_month=month,
                               sample_summary=summarize_transactions(sample_month_transactions(rows, month)))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
                flash("Enter a valid email address.", "error")
            elif len(password) < 10 or len(password) > 128:
                flash("Use a password between 10 and 128 characters.", "error")
            else:
                db.session.add(User(email=email, password_hash=generate_password_hash(password)))
                try:
                    db.session.commit()
                    flash("Account created. You can sign in now.", "success")
                    return redirect(url_for("login"))
                except IntegrityError:
                    db.session.rollback()
                    flash("An account already uses that email address.", "error")
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
            if user and check_password_hash(user.password_hash, request.form.get("password", "")):
                session.clear()
                session["user_id"] = user.id
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("dashboard"))
            flash("Email or password was incorrect.", "error")
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have signed out.", "success")
        return redirect(url_for("home"))

    def summary_for(month):
        query = month_query(Transaction.query.filter_by(user_id=g.user.id), month)
        return summarize_transactions(query.all())

    def dashboard_filters(default_month=""):
        month = parse_month(request.args.get("month", default_month))
        category = request.args.get("category", "")
        if category and category not in EXPENSE_CATEGORIES and category != "Income":
            abort(400)
        sort = request.args.get("sort", "newest")
        if sort not in TRANSACTION_SORT_ORDERS:
            abort(400)
        return month, category, sort

    def dashboard_page(transactions, summary, month, category, sort, *, demo=False):
        return render_template("dashboard.html", transactions=transactions, summary=summary,
                               month=month.isoformat()[:7] if month else "",
                               category=category, sort=sort, demo=demo,
                               today=date.today().isoformat())

    @app.get("/dashboard")
    @login_required
    def dashboard():
        try:
            month, category, sort = dashboard_filters()
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("dashboard"))
        query = month_query(Transaction.query.filter_by(user_id=g.user.id), month)
        if category:
            query = query.filter_by(category=category)
        field, descending = TRANSACTION_SORT_ORDERS[sort]
        column = getattr(Transaction, field)
        order = (column.desc(), Transaction.id.desc()) if descending else (column.asc(), Transaction.id.asc())
        return dashboard_page(query.order_by(*order).all(), summary_for(month), month, category, sort)

    @app.get("/demo")
    def demo():
        rows = sample_transactions()
        latest_month = max(item.occurred_on for item in rows).isoformat()[:7]
        try:
            month, category, sort = dashboard_filters(latest_month)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("demo"))
        month_rows = sample_month_transactions(rows, month)
        visible_rows = [item for item in month_rows if not category or item.category == category]
        field, descending = TRANSACTION_SORT_ORDERS[sort]
        visible_rows.sort(key=attrgetter(field), reverse=descending)
        return dashboard_page(visible_rows, summarize_transactions(month_rows), month, category, sort, demo=True)

    @app.get("/demo/export.csv")
    def export_demo_csv():
        try:
            month = parse_month(request.args.get("month", ""))
        except ValueError:
            abort(400)
        rows = sample_month_transactions(sample_transactions(), month)
        rows.sort(key=attrgetter("occurred_on"))
        return transaction_csv(rows, "budget-compass-sample.csv")

    @app.post("/transactions")
    @login_required
    def create_transaction():
        try:
            values = parse_transaction(request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("dashboard"))
        db.session.add(Transaction(user_id=g.user.id, **values))
        db.session.commit()
        flash("Transaction added.", "success")
        return redirect(url_for("dashboard"))

    def owned_transaction(transaction_id):
        item = db.session.get(Transaction, transaction_id)
        if not item or item.user_id != g.user.id:
            abort(404)
        return item

    @app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_transaction(transaction_id):
        item = owned_transaction(transaction_id)
        if request.method == "POST":
            try:
                values = parse_transaction(request.form)
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                for key, value in values.items():
                    setattr(item, key, value)
                db.session.commit()
                flash("Transaction updated.", "success")
                return redirect(url_for("dashboard"))
        return render_template("edit.html", item=item)

    @app.post("/transactions/<int:transaction_id>/delete")
    @login_required
    def delete_transaction(transaction_id):
        db.session.delete(owned_transaction(transaction_id))
        db.session.commit()
        flash("Transaction deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.post("/transactions/import")
    @login_required
    def import_csv():
        upload = request.files.get("file")
        if not upload or not upload.filename.lower().endswith(".csv"):
            flash("Choose a CSV file.", "error")
            return redirect(url_for("dashboard"))
        try:
            contents = upload.stream.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(contents, newline=""), strict=True)
            if not reader.fieldnames or tuple(reader.fieldnames) != CSV_FIELDS:
                raise ValueError("CSV columns must be: date,type,name,category,amount.")
            values = []
            for index, row in enumerate(reader, 1):
                if index > MAX_IMPORT_ROWS:
                    raise ValueError("Import at most 500 rows at a time.")
                if None in row:
                    raise ValueError(f"Row {index}: too many columns.")
                try:
                    values.append(parse_transaction(row))
                except ValueError as exc:
                    raise ValueError(f"Row {index}: {exc}") from None
            if not values:
                raise ValueError("The CSV contains no transactions.")
        except (UnicodeDecodeError, csv.Error, ValueError) as exc:
            flash(f"Import failed: {exc}", "error")
            return redirect(url_for("dashboard"))
        db.session.add_all(Transaction(user_id=g.user.id, **item) for item in values)
        db.session.commit()
        flash(f"Imported {len(values)} transactions.", "success")
        return redirect(url_for("dashboard"))

    @app.get("/transactions/export.csv")
    @login_required
    def export_csv():
        try:
            month = parse_month(request.args.get("month", ""))
        except ValueError:
            abort(400)
        rows = month_query(Transaction.query.filter_by(user_id=g.user.id), month).order_by(
            Transaction.occurred_on, Transaction.id).all()
        return transaction_csv(rows, "budget-compass.csv")

    @app.get("/api/summary")
    def summary_api():
        if g.user is None:
            return jsonify(error="Sign in required."), 401
        try:
            month = parse_month(request.args.get("month", ""))
        except ValueError:
            return jsonify(error="Invalid month; use YYYY-MM."), 400
        return jsonify(month=month.strftime("%Y-%m") if month else None, **summary_for(month))

    @app.get("/health")
    def health():
        db.session.execute(db.select(func.count(User.id))).scalar_one()
        return jsonify(status="ok")

    @app.errorhandler(413)
    def too_large(error):
        return render_template("error.html", message="The uploaded file is too large (1 MB maximum)."), 413

    @app.errorhandler(400)
    @app.errorhandler(404)
    def bad_request(error):
        return render_template("error.html", message=getattr(error, "description", "Page not found.")), error.code

    with app.app_context():
        if database_schema:
            with db.engine.begin() as connection:
                connection.execute(CreateSchema(database_schema, if_not_exists=True))
        db.create_all()
    return app
