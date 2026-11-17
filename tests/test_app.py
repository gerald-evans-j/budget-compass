import io
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
