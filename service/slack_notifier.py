"""
Posts incident briefs to Slack via an Incoming Webhook.

If SLACK_WEBHOOK_URL isn't set, falls back to printing the message locally
so the rest of the pipeline is runnable/demoable before you've set up a
real Slack workspace. Set SLACK_WEBHOOK_URL once you have a real webhook
(Slack App -> Incoming Webhooks -> Add New Webhook to Workspace).
"""
import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def _render_blocks(blocks: list) -> str:
    lines = []
    for block in blocks:
        if block["type"] in ("section",):
            lines.append(block["text"]["text"])
        elif block["type"] == "header":
            lines.append(block["text"]["text"])
        elif block["type"] == "context":
            lines.append(" | ".join(e["text"] for e in block["elements"]))
        elif block["type"] == "divider":
            lines.append("-" * 40)
    return "\n\n".join(lines)


def _post(payload: dict, print_text: str):
    if not SLACK_WEBHOOK_URL:
        print("=" * 60)
        print("[slack_notifier] SLACK_WEBHOOK_URL not set -- printing instead:")
        print(print_text)
        print("=" * 60)
        return

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Slack webhook returned status {resp.status}")


def post_message(text: str):
    _post({"text": text}, print_text=text)


def post_blocks(blocks: list, fallback_text: str):
    """fallback_text is Slack's required plain-text summary (shown in
    notifications/unfurls); the console fallback renders the full blocks
    instead, since that's how we've been verifying the pipeline without a
    real Slack workspace."""
    _post({"text": fallback_text, "blocks": blocks}, print_text=_render_blocks(blocks))
