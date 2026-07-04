"""
Generates a synthetic metrics time series (requests/min, errors/min, latency)
per endpoint, with a flat noisy baseline that spikes on the GET /<code>
endpoint starting at the seeded bug's deploy time and continuing to "now"
(the bug is never fixed in this synthetic history -- that's the incident
we're about to detect and respond to).

Run: `python simulator/metrics_generator.py`
Writes metrics.json to the project root and prints a small before/after
summary so you can eyeball that the spike lines up with the bad deploy.
"""
import json
import os
import random
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BUCKET_MINUTES = 15
LOOKBACK_DAYS_BEFORE_ANOMALY = 3

ENDPOINTS = ["GET /<code>", "POST /shorten", "GET /stats/<code>", "GET /health"]

# Baseline (pre-anomaly, and always for unaffected endpoints) request volume
# and error rate per endpoint. Error rate here is "normal" 404s from typos,
# bad codes, etc. -- not a sign of trouble.
BASELINE = {
    "GET /<code>": {"requests_per_min": 65, "error_rate": 0.02, "latency_ms": 45},
    "POST /shorten": {"requests_per_min": 12, "error_rate": 0.01, "latency_ms": 60},
    "GET /stats/<code>": {"requests_per_min": 8, "error_rate": 0.01, "latency_ms": 35},
    "GET /health": {"requests_per_min": 20, "error_rate": 0.0, "latency_ms": 5},
}

# Once the bug is live, GET /<code> starts failing on almost every request
# whose link has survived long enough to hit the background cleanup thread.
INCIDENT_ERROR_RATE = 0.72


def load_ground_truth():
    with open(os.path.join(ROOT, "ground_truth.json")) as f:
        return json.load(f)


def generate():
    gt = load_ground_truth()
    anomaly_start = datetime.fromisoformat(gt["bug_deploy_time"])
    now = datetime.now().replace(microsecond=0)

    start = anomaly_start - timedelta(days=LOOKBACK_DAYS_BEFORE_ANOMALY)
    rows = []
    t = start
    while t <= now:
        for endpoint in ENDPOINTS:
            base = BASELINE[endpoint]
            requests = max(0, round(random.gauss(base["requests_per_min"], base["requests_per_min"] * 0.15)))

            error_rate = base["error_rate"]
            latency_ms = base["latency_ms"]
            if endpoint == gt["affected_endpoint"] and t >= anomaly_start:
                error_rate = INCIDENT_ERROR_RATE + random.uniform(-0.05, 0.05)
                latency_ms = base["latency_ms"] * 1.2  # KeyError -> 500 fails fast, slight overhead only

            error_rate = min(max(error_rate, 0.0), 1.0)
            errors = round(requests * error_rate)

            rows.append({
                "timestamp": t.isoformat(),
                "endpoint": endpoint,
                "requests": requests,
                "errors": errors,
                "latency_ms": round(random.gauss(latency_ms, latency_ms * 0.1), 1),
            })
        t += timedelta(minutes=BUCKET_MINUTES)

    out_path = os.path.join(ROOT, "metrics.json")
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=2)

    print(f"Wrote {len(rows)} metric buckets to {out_path}")
    print(f"Anomaly start (bug deploy time): {anomaly_start.isoformat()}")
    print(f"Affected endpoint: {gt['affected_endpoint']}")

    _print_before_after_summary(rows, gt["affected_endpoint"], anomaly_start)


def _print_before_after_summary(rows, affected_endpoint, anomaly_start):
    before = [r for r in rows if r["endpoint"] == affected_endpoint
              and datetime.fromisoformat(r["timestamp"]) < anomaly_start]
    after = [r for r in rows if r["endpoint"] == affected_endpoint
             and datetime.fromisoformat(r["timestamp"]) >= anomaly_start]

    def error_rate(bucket_list):
        total_req = sum(b["requests"] for b in bucket_list)
        total_err = sum(b["errors"] for b in bucket_list)
        return (total_err / total_req) if total_req else 0.0

    print(f"\n{affected_endpoint} error rate BEFORE anomaly_start: {error_rate(before):.1%}")
    print(f"{affected_endpoint} error rate AFTER  anomaly_start: {error_rate(after):.1%}")


if __name__ == "__main__":
    generate()
