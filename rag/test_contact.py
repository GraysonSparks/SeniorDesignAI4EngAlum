"""Check the follow-up form endpoint (Story 11) without touching the real requests file.

    python test_contact.py
"""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import config

VALID = {"first_name": " Test ", "last_name": "Visitor", "email": "test.visitor@example.com",
         "phone": "", "message": "Interested in an endowed scholarship.", "staff": "", "consent": True}

# (what is being checked, changes to the valid request, expected status)
CASES = [
    ("valid request", {}, 200),
    ("routed to a staff member in the directory", {"staff": "Jon Sirico"}, 200),
    ("no consent", {"consent": False}, 422),
    ("blank first name", {"first_name": "   "}, 422),
    ("malformed email", {"email": "not-an-email"}, 422),
    ("staff member not in the directory", {"staff": "Someone Else"}, 422),
    ("message over 1000 characters", {"message": "x" * 1001}, 422),
]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        config.CONTACT_REQUESTS_FILE = Path(tmp) / "contact_requests.jsonl"
        from app import app  # imported after the override so nothing is written to rag/data/

        client = TestClient(app)
        failed = 0
        for label, changes, expected in CASES:
            status = client.post("/contact", json={**VALID, **changes}).status_code
            failed += status != expected
            print(f"{'ok  ' if status == expected else 'FAIL'} {label}: {status} (expected {expected})")

        stored = [json.loads(l) for l in config.CONTACT_REQUESTS_FILE.read_text().splitlines()]
        expected_keys = {"received", "first_name", "last_name", "email", "phone", "message", "staff"}
        checks = [
            ("only the accepted requests were stored", len(stored) == 2),
            ("stored fields are exactly the form fields plus a timestamp",
             all(set(r) == expected_keys for r in stored)),
            ("whitespace is trimmed", stored[0]["first_name"] == "Test"),
        ]
        for label, ok in checks:
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {label}")
        print(f"\n{len(CASES) + len(checks) - failed}/{len(CASES) + len(checks)} passed")
        raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
