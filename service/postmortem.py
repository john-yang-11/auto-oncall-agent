"""
M7: auto-generated postmortem.

Given a resolved incident's stored record, draft a markdown postmortem in
the standard structure (summary, timeline, root cause, impact, action
items) -- grounded only in facts already captured during the incident, not
free-form invention. Always a draft for human review before it's real.

Run: `python service/postmortem.py <incident_id>`
"""
import os
import sys
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from incident_store import get_incident, mark_resolved

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTMORTEMS_DIR = os.path.join(ROOT, "postmortems")

MODEL = "claude-sonnet-5"

PROMPT_TEMPLATE = """Draft a blameless postmortem for the incident below, using only the facts \
given -- do not invent details, names, or numbers that aren't provided. This is a \
draft for a human to review and edit before it's published, so it's fine to leave \
placeholders like "[owner TBD]" for anything not in the record.

Incident facts:
- Incident ID: {incident_id}
- Detected at: {created_at}
- Endpoint: {endpoint}
- Alert first seen: {first_seen}
- Alert message: {alert_message}
- Suspect commit: {suspect_sha} -- {suspect_commit_message}
- Suspect-commit reasoning (from automated triage): {suspect_reasoning}
- Matched runbook: {runbook_filename}
- Impact: {impact}
- Resolved at: {resolved_at}

Write the postmortem in this structure (markdown):
# Postmortem: <short title>
## Summary
## Timeline
## Root Cause
## Impact
## What Went Well / What Went Wrong
## Action Items

Keep the root-cause section honest about the fact that the suspect commit was \
identified by automated correlation + LLM review of the diff, not by a human-verified \
root-cause investigation -- phrase it as "most likely cause" not a certainty.
"""


def generate_postmortem(incident_id: str, resolved_at: str = None) -> str:
    incident = get_incident(incident_id)
    if incident is None:
        raise ValueError(f"No incident found with id {incident_id}")

    prompt = PROMPT_TEMPLATE.format(
        incident_id=incident["id"],
        created_at=incident["created_at"],
        endpoint=incident["endpoint"],
        first_seen=incident["first_seen"],
        alert_message=incident["alert_message"],
        suspect_sha=incident["suspect_sha"][:8],
        suspect_commit_message=incident["suspect_commit_message"],
        suspect_reasoning=incident["suspect_reasoning"],
        runbook_filename=incident["runbook_filename"] or "none matched",
        impact=incident["impact"],
        resolved_at=resolved_at or "just now",
    )

    client = Anthropic()
    response = client.messages.create(
        model=MODEL, max_tokens=1200, messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def resolve_incident(incident_id: str) -> str:
    """Generate the postmortem, save it to disk, and mark the incident resolved."""
    os.makedirs(POSTMORTEMS_DIR, exist_ok=True)
    resolved_at = datetime.now().isoformat()
    postmortem_text = generate_postmortem(incident_id, resolved_at=resolved_at)

    path = os.path.join(POSTMORTEMS_DIR, f"{incident_id}.md")
    with open(path, "w") as f:
        f.write(postmortem_text)

    mark_resolved(incident_id, postmortem_path=path)
    return path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python service/postmortem.py <incident_id>")
        raise SystemExit(1)
    path = resolve_incident(sys.argv[1])
    print(f"Postmortem written to {path}")
