"""
M3: LLM-assisted suspect-commit identification.

Given an alert (endpoint + when it started), find the most recent deploy
that was live at that time, pull that commit's diff, and ask Claude to
judge whether it's a plausible cause -- hedged and cited, never asserted
as a confirmed root cause. This is deploy-correlation + LLM reasoning,
not git-bisect: real incidents rarely offer a reproducible failing test
to bisect against.
"""
import json
import os
import subprocess
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOY_APP = os.path.join(ROOT, "toy_app")

MODEL = "claude-sonnet-5"

PROMPT_TEMPLATE = """An alert fired for the production service below. Your job is to judge \
whether the given commit is a plausible cause -- you are not confirming a root \
cause, you are ranking a suspect for a human to verify.

Alert:
- Endpoint: {endpoint}
- First seen: {first_seen}
- Message: {message}

Most recent commit deployed before the alert (the prime suspect, since it's \
the last thing that changed):
- SHA: {sha}
- Message: {commit_message}

Diff:
```
{diff}
```
{runbook_section}
In 3-5 sentences: is this commit a plausible cause of the alert? Cite the \
specific lines/changes that support your judgment. Explicitly state your \
confidence (e.g. "likely", "possible but uncertain", "doesn't look related") \
-- do not claim certainty you don't have.
"""

RUNBOOK_SECTION_TEMPLATE = """
A runbook matching this alert's symptoms was found (for context, not proof):
{runbook_text}
"""


def find_preceding_deploy(endpoint_first_seen: datetime, deploys: dict) -> str:
    """Return the SHA of the most recent deploy at or before first_seen."""
    candidates = [
        (sha, datetime.fromisoformat(ts))
        for sha, ts in deploys.items()
    ]
    candidates = [c for c in candidates if c[1] <= endpoint_first_seen]
    if not candidates:
        candidates = [
            (sha, datetime.fromisoformat(ts)) for sha, ts in deploys.items()
        ]
    return max(candidates, key=lambda c: c[1])[0]


def get_commit_message(sha: str) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%s", sha],
        cwd=TOY_APP, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL,
    ).stdout.strip()


def get_diff(sha: str) -> str:
    return subprocess.run(
        ["git", "show", sha],
        cwd=TOY_APP, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL,
    ).stdout


def analyze(endpoint: str, first_seen: datetime, message: str, runbook_text: str = None) -> dict:
    with open(os.path.join(ROOT, "deploys.json")) as f:
        deploys = json.load(f)

    sha = find_preceding_deploy(first_seen, deploys)
    commit_message = get_commit_message(sha)
    diff = get_diff(sha)

    runbook_section = (
        RUNBOOK_SECTION_TEMPLATE.format(runbook_text=runbook_text) if runbook_text else ""
    )
    prompt = PROMPT_TEMPLATE.format(
        endpoint=endpoint, first_seen=first_seen.isoformat(), message=message,
        sha=sha[:8], commit_message=commit_message, diff=diff,
        runbook_section=runbook_section,
    )
    client = Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    reasoning = response.content[0].text

    return {"sha": sha, "commit_message": commit_message, "reasoning": reasoning}


if __name__ == "__main__":
    result = analyze(
        endpoint="GET /<code>",
        first_seen=datetime.fromisoformat("2026-06-26T23:24:47"),
        message="Error rate 71% on GET /<code>, exceeds 20% threshold",
    )
    print(f"Suspect commit: {result['sha'][:8]} -- {result['commit_message']}")
    print(f"\nReasoning:\n{result['reasoning']}")
