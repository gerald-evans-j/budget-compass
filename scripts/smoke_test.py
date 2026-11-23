"""Exercise a running Budget Compass instance using fictional data.

Usage: python scripts/smoke_test.py http://127.0.0.1:8000
Creates one test account, exercises its transactions, and removes those entries.
"""

import csv
import http.cookiejar
import io
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date


def main(base_url):
    base_url = base_url.rstrip("/")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(path):
        with opener.open(base_url + path, timeout=90) as response:
            return response.read().decode("utf-8")

    def token(page):
        match = re.search(r'name="csrf_token" value="([^"]+)"', page)
        assert match, "No form token found"
        return match.group(1)

    def post(path, fields):
        request = urllib.request.Request(base_url + path,
            data=urllib.parse.urlencode(fields).encode("utf-8"))
        with opener.open(request, timeout=90) as response:
            return response.read().decode("utf-8")

    for attempt in range(30):
        try:
            assert json.loads(get("/health")) == {"status": "ok"}
            break
        except (urllib.error.URLError, TimeoutError):
            if attempt == 29:
                raise
            time.sleep(1)
    assert "$560.47" in get("/demo"), "Sample dashboard totals differ"
    email = f"smoke-{secrets.token_hex(8)}@example.test"
    password = secrets.token_urlsafe(24)
    page = post("/register", {"csrf_token": token(get("/register")),
        "email": email, "password": password})
    assert "Account created" in page
    page = post("/login", {"csrf_token": token(page), "email": email, "password": password})
    assert "Add transaction" in page
    today = date.today().isoformat()
    for kind, name, category, amount in (("income", "Campus work", "Income", "250.00"),
                                         ("expense", "Lunch", "Food", "12.50")):
        page = post("/transactions", {"csrf_token": token(page), "type": kind,
            "name": name, "category": category, "amount": amount, "date": today})
    summary = json.loads(get("/api/summary?month=" + today[:7]))
    assert (summary["income_cents"], summary["expenses_cents"], summary["balance_cents"]) == (25000, 1250, 23750)
    exported = list(csv.DictReader(io.StringIO(get("/transactions/export.csv"))))
    assert len(exported) == 2
    assert {item["name"] for item in exported} == {"Campus work", "Lunch"}
    ids = re.findall(r'href="/transactions/(\d+)/edit"', page)
    assert len(ids) == 2
    edit_path = f"/transactions/{ids[0]}/edit"
    page = post(edit_path, {"csrf_token": token(get(edit_path)), "type": "expense",
        "name": "Updated entry", "category": "Food", "amount": "15.25", "date": today})
    assert "Transaction updated" in page
    for item_id in ids:
        page = post(f"/transactions/{item_id}/delete", {"csrf_token": token(page)})
    summary = json.loads(get("/api/summary"))
    assert summary["income_cents"] == summary["expenses_cents"] == summary["balance_cents"] == 0
    post("/logout", {"csrf_token": token(page)})
    try:
        get("/api/summary")
        raise AssertionError("Summary was accessible after sign-out")
    except urllib.error.HTTPError as exc:
        assert exc.code == 401
    print("PASS: health, demo, register/login, add, totals, CSV export, edit, delete, and logout")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/smoke_test.py BASE_URL")
    main(sys.argv[1])
