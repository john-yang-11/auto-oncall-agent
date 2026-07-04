"""
M8 (GitHub stretch): fetch real commit history via the GitHub REST API,
instead of local `git` calls against the toy repo.

GITHUB_REPO must be set to "owner/name" in .env. GITHUB_TOKEN is optional
for public repos (raises the rate limit) but required for private ones.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.github.com"


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _repo():
    repo = os.environ.get("GITHUB_REPO")
    if not repo:
        raise RuntimeError("GITHUB_REPO not set in .env (expected 'owner/name')")
    return repo


def get_latest_commit(branch: str = None) -> dict:
    url = f"{API_BASE}/repos/{_repo()}/commits"
    params = {"per_page": 1}
    if branch:
        params["sha"] = branch
    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    commit = resp.json()[0]
    return {
        "sha": commit["sha"],
        "message": commit["commit"]["message"].splitlines()[0],
        "date": commit["commit"]["committer"]["date"],
    }


def get_diff(sha: str) -> str:
    url = f"{API_BASE}/repos/{_repo()}/commits/{sha}"
    headers = {**_headers(), "Accept": "application/vnd.github.v3.diff"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.text


if __name__ == "__main__":
    latest = get_latest_commit()
    print(f"Latest commit on {_repo()}: {latest['sha'][:8]} ({latest['date']})")
    print(f"  {latest['message']}")
    diff = get_diff(latest["sha"])
    print(f"\nDiff length: {len(diff)} chars")
    print(diff[:500])
