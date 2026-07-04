"""
Watches metrics.json for an endpoint whose recent error rate has crossed a
threshold and is still elevated at the most recent bucket (i.e. an ongoing
issue, not a one-off blip), then POSTs an alert to the webhook -- the way a
real monitoring tool's alert rule would.

Run: `python simulator/fire_alert.py` (with the FastAPI server already running)
"""
import json
import os
from datetime import datetime

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBHOOK_URL = "http://127.0.0.1:8000/alert"
ERROR_RATE_THRESHOLD = 0.20

# Real monitoring tools (Sentry, Datadog, etc.) capture the actual exception
# alongside the error-rate spike, not just a bare count -- this mirrors that,
# rather than handing the alert a made-up root cause.
SAMPLE_EXCEPTIONS = {
    "GET /<code>": "KeyError raised from an unhandled lookup miss -- requests are "
                    "failing with 500 instead of a normal 404 for missing/expired codes.",
}


def find_ongoing_anomaly():
    with open(os.path.join(ROOT, "metrics.json")) as f:
        rows = json.load(f)

    by_endpoint = {}
    for row in rows:
        by_endpoint.setdefault(row["endpoint"], []).append(row)

    for endpoint, buckets in by_endpoint.items():
        buckets.sort(key=lambda b: b["timestamp"])
        latest = buckets[-1]
        if latest["requests"] == 0 or latest["errors"] / latest["requests"] < ERROR_RATE_THRESHOLD:
            continue

        # Walk backward from the end while error rate stays elevated, to find
        # when this specific run of bad buckets started.
        first_seen = latest["timestamp"]
        for bucket in reversed(buckets):
            rate = bucket["errors"] / bucket["requests"] if bucket["requests"] else 0
            if rate < ERROR_RATE_THRESHOLD:
                break
            first_seen = bucket["timestamp"]

        return endpoint, first_seen, latest

    return None


if __name__ == "__main__":
    result = find_ongoing_anomaly()
    if result is None:
        print("No ongoing anomaly found above threshold -- nothing to fire.")
        raise SystemExit(0)

    endpoint, first_seen, latest = result
    error_rate = latest["errors"] / latest["requests"]
    message = f"Error rate {error_rate:.0%} on {endpoint}, exceeds {ERROR_RATE_THRESHOLD:.0%} threshold."
    if endpoint in SAMPLE_EXCEPTIONS:
        message += f" Sample exception: {SAMPLE_EXCEPTIONS[endpoint]}"
    payload = {
        "endpoint": endpoint,
        "first_seen": first_seen,
        "message": message,
    }
    resp = requests.post(WEBHOOK_URL, json=payload)
    print(f"POSTed alert: {payload}")
    print(f"Response: {resp.status_code} {resp.json()}")
