"""
M5: impact estimation from the synthetic metrics.

Honest, simple arithmetic over metrics.json -- not a real SLO/error-budget
engine. Compares the affected endpoint's error rate before vs. during the
incident, and how much of total traffic that endpoint carries. No pandas:
metrics.json is a few thousand rows, plain Python dicts are enough.
"""
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_metrics():
    with open(os.path.join(ROOT, "metrics.json")) as f:
        return json.load(f)


def estimate_impact(endpoint: str, first_seen: datetime) -> dict:
    rows = _load_metrics()

    before = [r for r in rows if r["endpoint"] == endpoint
              and datetime.fromisoformat(r["timestamp"]) < first_seen]
    during = [r for r in rows if r["endpoint"] == endpoint
              and datetime.fromisoformat(r["timestamp"]) >= first_seen]
    during_all_endpoints = [r for r in rows
                             if datetime.fromisoformat(r["timestamp"]) >= first_seen]

    def error_rate(bucket_list):
        total_req = sum(b["requests"] for b in bucket_list)
        total_err = sum(b["errors"] for b in bucket_list)
        return (total_err / total_req) if total_req else 0.0

    baseline_rate = error_rate(before)
    incident_rate = error_rate(during)
    affected_requests = sum(b["requests"] for b in during)
    affected_errors = sum(b["errors"] for b in during)
    total_requests_all_endpoints = sum(b["requests"] for b in during_all_endpoints)
    traffic_share = (
        affected_requests / total_requests_all_endpoints
        if total_requests_all_endpoints else 0.0
    )

    return {
        "baseline_error_rate": baseline_rate,
        "incident_error_rate": incident_rate,
        "error_rate_multiple": (incident_rate / baseline_rate) if baseline_rate > 0 else None,
        "affected_requests": affected_requests,
        "affected_errors": affected_errors,
        "traffic_share": traffic_share,
    }


def format_impact_line(impact: dict) -> str:
    multiple = impact["error_rate_multiple"]
    multiple_str = f"{multiple:.0f}x" if multiple else "n/a"
    return (
        f"Error rate {impact['incident_error_rate']:.0%} "
        f"(baseline {impact['baseline_error_rate']:.0%}, {multiple_str} increase). "
        f"~{impact['affected_errors']:,} failed requests so far on an endpoint "
        f"carrying {impact['traffic_share']:.0%} of total traffic since the incident began."
    )


if __name__ == "__main__":
    impact = estimate_impact("GET /<code>", datetime.fromisoformat("2026-06-26T23:24:47"))
    print(impact)
    print()
    print(format_impact_line(impact))
