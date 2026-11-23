import io
import os
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

from app import Transaction, User, create_app, db


class BudgetCompassTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-only-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(self.tempdir.name, "test.db"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def token(self):
        with self.client.session_transaction() as sess:
            return sess["csrf_token"]

    def register_and_login(self, email="student@example.edu"):
        self.client.get("/register")
        result = self.client.post("/register", data={"csrf_token": self.token(),
            "email": email, "password": "a secure password"}, follow_redirects=True)
        self.assertIn(b"Account created", result.data)
        self.client.post("/login", data={"csrf_token": self.token(),
            "email": email, "password": "a secure password"}, follow_redirects=True)

    def add(self, *, kind="expense", name="Lunch", amount="12.50", category="Food", occurred="2026-09-05"):
        return self.client.post("/transactions", data={"csrf_token": self.token(),
            "type": kind, "name": name, "amount": amount,
            "category": category, "date": occurred}, follow_redirects=True)

    def test_account_login_and_password_hash(self):
        self.register_and_login()
        with self.app.app_context():
            user = db.session.execute(db.select(User)).scalar_one()
            self.assertNotIn("a secure password", user.password_hash)
        self.assertIn(b"Dashboard", self.client.get("/dashboard").data)
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.assertEqual(self.client.get("/api/summary").status_code, 401)

    def test_transactions_summary_filter_edit_delete_and_export(self):
        self.register_and_login()
        self.add(kind="income", name="Campus job", amount="250.00", category="Income")
        self.add()
        self.add(name="Books", amount="35.00", category="School", occurred="2026-08-20")
        summary = self.client.get("/api/summary?month=2026-09").json
        self.assertEqual((summary["income_cents"], summary["expenses_cents"], summary["balance_cents"]),
                         (25000, 1250, 23750))
        self.assertEqual(summary["by_category_cents"], {"Food": 1250})
        page = self.client.get("/dashboard?month=2026-09&category=Food&sort=high")
        self.assertIn(b"Lunch", page.data)
        self.assertNotIn(b"Books", page.data)
        csv_result = self.client.get("/transactions/export.csv?month=2026-09")
        self.assertEqual(csv_result.status_code, 200)
        self.assertIn(b"Campus job", csv_result.data)
        self.assertNotIn(b"Books", csv_result.data)
        with self.app.app_context():
            lunch_id = db.session.execute(db.select(Transaction).filter_by(name="Lunch")).scalar_one().id
        self.client.post(f"/transactions/{lunch_id}/edit", data={"csrf_token": self.token(),
            "type": "expense", "name": "Lunch", "amount": "15.25", "category": "Food",
            "date": "2026-09-05"})
        self.assertEqual(self.client.get("/api/summary?month=2026-09").json["expenses_cents"], 1525)
        self.client.post(f"/transactions/{lunch_id}/delete", data={"csrf_token": self.token()})
        self.assertEqual(self.client.get("/api/summary?month=2026-09").json["expenses_cents"], 0)

    def test_user_cannot_access_another_users_transactions(self):
        self.register_and_login("first@example.edu")
        self.add()
        with self.app.app_context():
            item_id = db.session.execute(db.select(Transaction)).scalar_one().id
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.register_and_login("second@example.edu")
        self.assertEqual(self.client.get(f"/transactions/{item_id}/edit").status_code, 404)
        self.assertEqual(self.client.post(f"/transactions/{item_id}/delete",
            data={"csrf_token": self.token()}).status_code, 404)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)
        self.assertNotIn(b"Lunch", self.client.get("/transactions/export.csv").data)

    def test_validation_and_csrf_reject_bad_changes(self):
        self.register_and_login()
        self.assertEqual(self.client.post("/transactions", data={}).status_code, 400)
        self.add(amount="3.001")
        self.add(amount="-1")
        self.add(kind="income", category="Food")
        self.add(occurred="not-a-date")
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)
        self.assertEqual(self.client.get("/api/summary?month=bad").status_code, 400)

    def test_import_is_atomic_and_export_protects_formula_text(self):
        self.register_and_login()
        good_row = "2026-09-06,expense,Bus,Transportation,2.50\n"
        invalid = "date,type,name,category,amount\n" + good_row + "2026-09-06,expense,Bad,Food,3.001\n"
        result = self.client.post("/transactions/import", data={"csrf_token": self.token(),
            "file": (io.BytesIO(invalid.encode()), "budget.csv")}, content_type="multipart/form-data", follow_redirects=True)
        self.assertIn(b"Import failed", result.data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)
        valid = "date,type,name,category,amount\n" + good_row + "2026-09-06,expense,=2+2,Food,1.00\n"
        result = self.client.post("/transactions/import", data={"csrf_token": self.token(),
            "file": (io.BytesIO(valid.encode()), "budget.csv")}, content_type="multipart/form-data", follow_redirects=True)
        self.assertIn(b"Imported 2 transactions", result.data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 350)
        self.assertIn(b"'=2+2", self.client.get("/transactions/export.csv").data)

    def test_health_and_public_pages(self):
        self.assertEqual(self.client.get("/health").json, {"status": "ok"})
        self.assertIn(b"Know where your money goes", self.client.get("/").data)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_public_demo_filters_sample_data_without_an_account(self):
        home = self.client.get("/")
        self.assertIn(b'href="/demo"', home.data)
        demo = self.client.get("/demo")
        self.assertEqual(demo.status_code, 200)
        self.assertIn(b"$560.47", demo.data)
        self.assertIn(b"Campus paycheck", demo.data)
        self.assertNotIn(b"Add transaction", demo.data)

        filtered = self.client.get("/demo?month=2026-09&category=Food&sort=high")
        self.assertIn(b"Lunch", filtered.data)
        self.assertNotIn(b"Bus fare", filtered.data)
        self.assertNotIn(b"Campus paycheck", filtered.data)
        sample_csv = self.client.get("/demo/export.csv?month=2026-09")
        self.assertIn(b"budget-compass-sample.csv", sample_csv.headers["Content-Disposition"].encode())
        self.assertIn(b"Bus fare", sample_csv.data)
        self.assertNotIn(b"Campus paycheck", sample_csv.data)
        with self.app.app_context():
            self.assertEqual(db.session.execute(db.select(User)).scalars().all(), [])
            self.assertEqual(db.session.execute(db.select(Transaction)).scalars().all(), [])

    def test_sample_csv_import_stays_in_the_signed_in_account(self):
        self.register_and_login()
        self.add(name="Private purchase")
        sample_csv = self.client.get("/demo/export.csv?month=2026-10").data
        self.assertNotIn(b"Private purchase", sample_csv)
        self.assertNotIn(b"Private purchase", self.client.get("/demo?month=").data)

        response = self.client.post("/transactions/import", data={
            "csrf_token": self.token(), "file": (io.BytesIO(sample_csv), "sample.csv")
        }, follow_redirects=True)
        self.assertIn(b"Imported 9 transactions", response.data)
        totals = self.client.get("/api/summary?month=2026-10").json
        self.assertEqual(totals["balance_cents"], 56047)
        self.assertIn(b"Campus paycheck", self.client.get("/transactions/export.csv?month=2026-10").data)

    def test_non_ascii_or_wrong_csrf_tokens_return_400(self):
        self.register_and_login()
        for token in ("wrong-token", "\u2717", "\u00e9", ""):
            with self.subTest(token=token):
                result = self.client.post("/transactions", data={"csrf_token": token})
                self.assertEqual(result.status_code, 400)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)

    def test_dates_require_documented_format_and_real_calendar_days(self):
        self.register_and_login()
        for value in ("20261123", "2026-W48-1", "2026-02-30", "2026-2-03", "0000-01-01"):
            with self.subTest(date=value):
                result = self.add(occurred=value)
                self.assertIn(b"Enter a valid date in YYYY-MM-DD format", result.data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)
        self.add(occurred="2028-02-29")
        self.assertEqual(self.client.get("/api/summary?month=2028-02").json["expenses_cents"], 1250)

    def test_duplicate_account_and_invalid_login_do_not_grant_access(self):
        self.register_and_login()
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.client.get("/register")
        duplicate = self.client.post("/register", data={"csrf_token": self.token(),
            "email": "STUDENT@example.edu", "password": "another secure password"}, follow_redirects=True)
        self.assertIn(b"An account already uses", duplicate.data)
        bad_login = self.client.post("/login", data={"csrf_token": self.token(),
            "email": "student@example.edu", "password": "wrong password"}, follow_redirects=True)
        self.assertIn(b"Email or password was incorrect", bad_login.data)
        self.assertEqual(self.client.get("/api/summary").status_code, 401)
        with self.app.app_context():
            self.assertEqual(db.session.query(User).count(), 1)

    def test_registration_rejects_invalid_email_and_password_length(self):
        self.client.get("/register")
        for email, password in (("invalid", "a secure password"),
                                ("student@example.edu", "short"),
                                ("student@example.edu", "p" * 129)):
            with self.subTest(email=email, length=len(password)):
                self.client.post("/register", data={"csrf_token": self.token(),
                    "email": email, "password": password})
        with self.app.app_context():
            self.assertEqual(db.session.query(User).count(), 0)

    def test_decimal_arithmetic_and_negative_balance_are_exact(self):
        self.register_and_login()
        self.add(kind="income", category="Income", amount="0.30")
        self.add(amount="0.10")
        self.add(amount="0.20")
        self.assertEqual(self.client.get("/api/summary").json["balance_cents"], 0)
        self.add(amount="1.01")
        self.assertEqual(self.client.get("/api/summary").json["balance_cents"], -101)

    def test_december_filter_excludes_january_and_other_months(self):
        self.register_and_login()
        self.add(name="December", amount="10.00", occurred="2026-12-31")
        self.add(name="January", amount="20.00", occurred="2027-01-01")
        self.assertEqual(self.client.get("/api/summary?month=2026-12").json["expenses_cents"], 1000)
        self.assertEqual(self.client.get("/api/summary?month=2027-01").json["expenses_cents"], 2000)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 3000)
        for month in ("0000-01", "9999-12", "2026-13", "2026-1"):
            with self.subTest(month=month):
                self.assertEqual(self.client.get("/api/summary?month=" + month).status_code, 400)

    def test_sort_and_category_filter_preserve_monthly_overview(self):
        self.register_and_login()
        self.add(name="Small lunch", amount="2.00")
        self.add(name="Large lunch", amount="20.00")
        self.add(name="Book", amount="50.00", category="School")
        high = self.client.get("/dashboard?category=Food&sort=high").data
        low = self.client.get("/dashboard?category=Food&sort=low").data
        self.assertLess(high.index(b"Large lunch"), high.index(b"Small lunch"))
        self.assertLess(low.index(b"Small lunch"), low.index(b"Large lunch"))
        self.assertNotIn(b"<strong>Book</strong>", high)
        self.assertIn(b"$72.00", high)

    def test_cross_account_edit_post_is_rejected_and_owner_data_unchanged(self):
        self.register_and_login("owner@example.edu")
        self.add()
        with self.app.app_context():
            item_id = db.session.execute(db.select(Transaction)).scalar_one().id
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.register_and_login("other@example.edu")
        result = self.client.post(f"/transactions/{item_id}/edit", data={
            "csrf_token": self.token(), "type": "expense", "name": "Changed",
            "amount": "99.00", "category": "Food", "date": "2026-09-05"})
        self.assertEqual(result.status_code, 404)
        with self.app.app_context():
            item = db.session.get(Transaction, item_id)
            self.assertEqual((item.name, item.amount_cents), ("Lunch", 1250))

    def test_invalid_edit_does_not_change_saved_transaction(self):
        self.register_and_login()
        self.add()
        with self.app.app_context():
            item_id = db.session.execute(db.select(Transaction)).scalar_one().id
        response = self.client.post(f"/transactions/{item_id}/edit", data={
            "csrf_token": self.token(), "type": "expense", "name": "Lunch",
            "amount": "-9.00", "category": "Food", "date": "2026-09-05"})
        self.assertIn(b"Amount must be greater than zero", response.data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 1250)

    def import_file(self, contents, filename="budget.csv"):
        with io.BytesIO(contents) as upload:
            result = self.client.post("/transactions/import", data={"csrf_token": self.token(),
                "file": (upload, filename)}, content_type="multipart/form-data", follow_redirects=True)
        result.request.input_stream.close()
        return result

    def test_csv_rejects_bad_headers_encoding_and_extra_columns(self):
        self.register_and_login()
        for contents in (b"name,amount\nLunch,12.50\n", b"\xff\xfeinvalid",
                         b"date,type,name,category,amount\n2026-09-05,expense,Lunch,Food,12.50,extra\n",
                         b"date,type,name,category,amount\n"):
            with self.subTest(contents=contents):
                self.assertIn(b"Import failed", self.import_file(contents).data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)

    def test_csv_row_limit_is_atomic(self):
        self.register_and_login()
        header = b"date,type,name,category,amount\n"
        row = b"2026-09-05,expense,Lunch,Food,1.00\n"
        self.assertIn(b"Import at most 500 rows", self.import_file(header + row * 501).data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)
        self.assertIn(b"Imported 500 transactions", self.import_file(header + row * 500).data)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 50000)

    def test_large_csv_returns_413_without_changing_data(self):
        self.register_and_login()
        result = self.import_file(b"x" * (1024 * 1024 + 1))
        self.assertEqual(result.status_code, 413)
        self.assertEqual(self.client.get("/api/summary").json["expenses_cents"], 0)

    def test_html_in_description_is_escaped_in_dashboard_and_edit_form(self):
        self.register_and_login()
        self.add(name="<script>alert(1)</script>")
        page = self.client.get("/dashboard").data
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn(b"<script>alert(1)</script>", page)
        with self.app.app_context():
            item_id = db.session.execute(db.select(Transaction)).scalar_one().id
        self.assertNotIn(b"<script>alert(1)</script>",
                         self.client.get(f"/transactions/{item_id}/edit").data)

    def test_signed_out_routes_protect_private_data(self):
        self.register_and_login()
        self.add(name="Private purchase")
        self.client.post("/logout", data={"csrf_token": self.token()})
        for path in ("/dashboard", "/transactions/export.csv", "/transactions/1/edit"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertNotIn(b"Private purchase", response.data)
        self.assertEqual(self.client.get("/api/summary").status_code, 401)

    def test_saved_data_survives_a_new_app_instance(self):
        self.register_and_login()
        self.add()
        second = create_app({"TESTING": True, "SECRET_KEY": "test-only-key",
            "SQLALCHEMY_DATABASE_URI": self.app.config["SQLALCHEMY_DATABASE_URI"]})
        try:
            with second.app_context():
                item = db.session.execute(db.select(Transaction)).scalar_one()
                self.assertEqual((item.name, item.amount_cents), ("Lunch", 1250))
        finally:
            with second.app_context():
                db.session.remove()
                db.engine.dispose()

    def test_fresh_install_creates_default_sqlite_folder(self):
        instance_dir = os.path.join(self.tempdir.name, "fresh", "instance")
        flask_app = Flask("app", instance_path=instance_dir)
        with patch("app.Flask", return_value=flask_app):
            second = create_app({"TESTING": True, "SECRET_KEY": "test-only-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///budget.db"})
        try:
            self.assertTrue(os.path.isfile(os.path.join(instance_dir, "budget.db")))
            self.assertEqual(second.test_client().get("/health").json, {"status": "ok"})
        finally:
            with second.app_context():
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
