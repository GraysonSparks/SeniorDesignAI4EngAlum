"""Store follow-up requests left through the widget's contact form (Story 11).

This is the only place visitor data is written. A request holds what the visitor typed into the
form and nothing else: no conversation text, IP address, or browser details. Storage is a local
JSON Lines file for the prototype; where requests live once the assistant is hosted (and who can
read them) is an Advancement decision, so everything goes through save_request().
"""

import json
import threading
from datetime import datetime, timezone

import config

_lock = threading.Lock()


def save_request(request: dict) -> None:
    """Append one request with a UTC timestamp."""
    record = {"received": datetime.now(timezone.utc).isoformat(timespec="seconds"), **request}
    config.CONTACT_REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(config.CONTACT_REQUESTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # Story 10 (notify Advancement staff of a new request) hooks in here once a delivery
    # channel exists on the hosting side.
