"""
M8 (GitHub stretch): receive real GitHub push webhooks.

GitHub signs every webhook payload with a shared secret (X-Hub-Signature-256).
The synthetic pipeline never had anything to verify -- deploys.json was just
a local file we trusted. A real webhook is an HTTP request from the public
internet, so it must be authenticated: if the signature doesn't match, the
request is rejected before we act on it.

Records the latest known push to latest_deploy.json (the real-world analog
of the seeded deploys.json) so commit_analyzer-style reasoning always has an
up-to-date "most recent deploy" to compare an alert against.

To actually receive events: expose this server publicly (e.g. via ngrok),
then add a webhook in the target repo's GitHub settings (Settings ->
Webhooks -> Add webhook) pointing at that public URL + /github/push, with
"application/json" content type and the same secret as GITHUB_WEBHOOK_SECRET.

Run: `uvicorn service.github_webhook:app --port 8001`
"""
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slack_notifier import post_message

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEST_DEPLOY_PATH = os.path.join(ROOT, "latest_deploy.json")

app = FastAPI()


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.post("/github/push")
async def receive_push(request: Request):
    body = await request.body()
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(500, "GITHUB_WEBHOOK_SECRET not configured")

    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(body, signature, secret):
        raise HTTPException(401, "Invalid signature")

    payload = json.loads(body)
    head_commit = payload.get("head_commit") or {}
    record = {
        "repo": payload.get("repository", {}).get("full_name"),
        "sha": head_commit.get("id"),
        "message": (head_commit.get("message") or "").splitlines()[0] if head_commit.get("message") else None,
        "pushed_at": head_commit.get("timestamp"),
        "recorded_at": datetime.now().isoformat(),
    }
    with open(LATEST_DEPLOY_PATH, "w") as f:
        json.dump(record, f, indent=2)

    post_message(f":package: New push recorded as latest deploy: `{record['sha'][:8] if record['sha'] else '?'}` -- {record['message']}")
    return {"status": "recorded", "sha": record["sha"]}
