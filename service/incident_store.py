"""
M6: incident persistence.

A single JSON file is plenty at this scale (a handful of incidents in a
demo/portfolio project) -- no need for SQLite or an ORM here.
"""
import json
import os
import uuid
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCIDENTS_PATH = os.path.join(ROOT, "incidents.json")


def _load_all() -> list:
    if not os.path.exists(INCIDENTS_PATH):
        return []
    with open(INCIDENTS_PATH) as f:
        return json.load(f)


def _save_all(incidents: list):
    with open(INCIDENTS_PATH, "w") as f:
        json.dump(incidents, f, indent=2, default=str)


def save_incident(record: dict) -> str:
    incident_id = uuid.uuid4().hex[:8]
    record = {"id": incident_id, "created_at": datetime.now().isoformat(), "resolved": False, **record}
    incidents = _load_all()
    incidents.append(record)
    _save_all(incidents)
    return incident_id


def get_incident(incident_id: str) -> dict:
    for incident in _load_all():
        if incident["id"] == incident_id:
            return incident
    return None


def mark_resolved(incident_id: str, postmortem_path: str):
    incidents = _load_all()
    for incident in incidents:
        if incident["id"] == incident_id:
            incident["resolved"] = True
            incident["resolved_at"] = datetime.now().isoformat()
            incident["postmortem_path"] = postmortem_path
            _save_all(incidents)
            return
    raise ValueError(f"No incident found with id {incident_id}")
