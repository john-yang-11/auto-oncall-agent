"""
Real alert ingestion (M2) + LLM-assisted suspect-commit identification (M3)
+ RAG-based runbook retrieval (M4) + impact estimation (M5) + a polished
Slack card and incident persistence (M6).

A single endpoint, POST /alert, that a monitoring tool (or our own
simulator/fire_alert.py) POSTs a JSON alert to. Receiving it: finds the
best-matching runbook by semantic search, looks up the most recent deploy
before the alert, asks Claude to judge whether that commit is a plausible
cause (grounded by the matched runbook, if any), estimates impact from the
metrics, posts a structured Block Kit card to Slack, and saves the full
incident record.

Run: `uvicorn service.alert_webhook:app --reload` (from the project root)
"""
import os
import sys
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commit_analyzer import analyze
from impact import estimate_impact, format_impact_line
from incident_store import save_incident
from runbook_search import search as search_runbooks
from slack_notifier import post_blocks

app = FastAPI()


class Alert(BaseModel):
    endpoint: str
    first_seen: datetime
    message: str


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_incident_blocks(alert: Alert, suspect: dict, runbook: dict, impact: dict, incident_id: str) -> list:
    runbook_text = (
        f"`{runbook['filename']}` (score={runbook['score']:.2f})"
        if runbook else "none found above confidence threshold"
    )
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"\U0001F6A8 Incident: elevated errors on {alert.endpoint}"}},
        _section(f"*First seen:* {alert.first_seen.isoformat()}\n*Alert message:* {alert.message}"),
        {"type": "divider"},
        _section(f"*Suspect commit:* `{suspect['sha'][:8]}` -- {suspect['commit_message']}\n*Reasoning:* {suspect['reasoning']}"),
        {"type": "divider"},
        _section(f"*Matched runbook:* {runbook_text}"),
        {"type": "divider"},
        _section(f"*Estimated impact:* {format_impact_line(impact)}"),
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Incident `{incident_id}` -- AI-drafted analysis, verify before acting."}]},
    ]


@app.post("/alert")
def receive_alert(alert: Alert):
    runbook = search_runbooks(alert.message)
    suspect = analyze(
        alert.endpoint, alert.first_seen, alert.message,
        runbook_text=runbook["text"] if runbook else None,
    )
    impact = estimate_impact(alert.endpoint, alert.first_seen)

    incident_id = save_incident({
        "endpoint": alert.endpoint,
        "first_seen": alert.first_seen,
        "alert_message": alert.message,
        "suspect_sha": suspect["sha"],
        "suspect_commit_message": suspect["commit_message"],
        "suspect_reasoning": suspect["reasoning"],
        "runbook_filename": runbook["filename"] if runbook else None,
        "runbook_score": runbook["score"] if runbook else None,
        "impact": impact,
    })

    blocks = build_incident_blocks(alert, suspect, runbook, impact, incident_id)
    fallback_text = f"Incident {incident_id}: elevated errors on {alert.endpoint}, suspect commit {suspect['sha'][:8]}"
    post_blocks(blocks, fallback_text)

    return {
        "status": "received",
        "incident_id": incident_id,
        "suspect_sha": suspect["sha"],
        "runbook": runbook["filename"] if runbook else None,
        "impact": impact,
    }
