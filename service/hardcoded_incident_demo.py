"""
M1: the dumbest possible full path, end to end.

No alert ingestion, no LLM reasoning, no retrieval yet -- just a hardcoded
incident summary and a hardcoded runbook reference, posted to Slack (or
printed, if SLACK_WEBHOOK_URL isn't set). This exists purely to prove the
Slack-posting leg of the pipeline works before anything else is wired up.

Run: `python service/hardcoded_incident_demo.py`
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slack_notifier import post_message

INCIDENT_SUMMARY = """:rotating_light: *Incident: Elevated 5xx on GET /<code>*

*Suspect commit:* `15a5ad8d` -- "Add background cleanup thread for expired links (finer-grained clock)"
*Likely cause:* Expiry timestamps are stored in seconds but compared in milliseconds, so links are purged almost immediately; the redirect route also switched to a direct dict lookup, turning the resulting miss into an unhandled 500 instead of a 404.
*Matched runbook:* runbooks/elevated-5xx-redirect.md
*Estimated impact:* ~72% error rate on GET /<code> (was ~2% baseline) -- this endpoint carries the majority of production traffic.

_This is a hardcoded placeholder brief (M1) -- later milestones replace every field above with values computed from the live alert, commit diff, retrieval, and metrics._
"""


if __name__ == "__main__":
    post_message(INCIDENT_SUMMARY)
