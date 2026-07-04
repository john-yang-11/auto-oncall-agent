"""
Seeds toy_app/ as its own git repo with a realistic commit history,
including one deliberately-introduced bug, and writes deploys.json
mapping each commit SHA to a fake deploy timestamp.

Run once: `python seed_toy_repo.py`
Safe to re-run: it wipes and rebuilds toy_app/ from scratch.
"""
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime, timedelta


def _on_rm_error(func, path, exc_info):
    # git marks object files read-only on Windows; clear that bit and retry.
    os.chmod(path, stat.S_IWRITE)
    func(path)

ROOT = os.path.dirname(os.path.abspath(__file__))
TOY_APP = os.path.join(ROOT, "toy_app")

NOW = datetime.now().replace(microsecond=0)

# Days-ago offset for each commit's deploy time (16 commits, bug is index 11 -> offset 7)
OFFSETS_DAYS_AGO = [18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 2]
BUG_COMMIT_INDEX = 11  # 0-indexed -> the 12th commit


def run_git(args, cwd, env=None):
    result = subprocess.run(
        ["git"] + args, cwd=cwd, env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {args} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def write_files(files: dict):
    for relpath, content in files.items():
        full = os.path.join(TOY_APP, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", newline="\n") as f:
            f.write(content)


def commit(message: str, when: datetime) -> str:
    date_str = when.strftime("%Y-%m-%dT%H:%M:%S")
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "John Yang"
    env["GIT_AUTHOR_EMAIL"] = "john@example.com"
    env["GIT_COMMITTER_NAME"] = "John Yang"
    env["GIT_COMMITTER_EMAIL"] = "john@example.com"
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str
    run_git(["add", "-A"], cwd=TOY_APP, env=env)
    run_git(["commit", "-m", message, "--date", date_str], cwd=TOY_APP, env=env)
    return run_git(["rev-parse", "HEAD"], cwd=TOY_APP, env=env)


# ---------------------------------------------------------------------------
# Progressive file states, one per commit
# ---------------------------------------------------------------------------

STEPS = []

STEPS.append((
    "Initial commit: basic Flask app skeleton",
    {
        "requirements.txt": "flask\n",
        "README.md": (
            "# ShortLink\n\n"
            "A tiny toy URL shortener used as the substrate for the "
            "incident-response-ai project.\n"
        ),
        "app.py": (
            "from flask import Flask\n\n"
            "app = Flask(__name__)\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Add in-memory link store",
    {
        "store.py": (
            "class LinkStore:\n"
            "    def __init__(self):\n"
            "        self._links = {}\n\n"
            "    def save(self, code, url):\n"
            "        self._links[code] = url\n\n"
            "    def get(self, code):\n"
            "        return self._links.get(code)\n"
        ),
    },
))

STEPS.append((
    "Add POST /shorten endpoint",
    {
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, jsonify, request\n\n"
            "from store import LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=6):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    code = generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Add GET /<code> redirect endpoint",
    {
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=6):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    code = generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    return redirect(url)\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Validate URL scheme on shorten",
    {
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=6):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    code = generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    return redirect(url)\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Support custom alias in /shorten",
    {
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=6):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    return redirect(url)\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Track click counts per link",
    {
        "store.py": (
            "class LinkStore:\n"
            "    def __init__(self):\n"
            "        self._links = {}\n"
            "        self._clicks = {}\n\n"
            "    def save(self, code, url):\n"
            "        self._links[code] = url\n"
            "        self._clicks[code] = 0\n\n"
            "    def get(self, code):\n"
            "        return self._links.get(code)\n\n"
            "    def record_click(self, code):\n"
            "        if code in self._clicks:\n"
            "            self._clicks[code] += 1\n\n"
            "    def get_clicks(self, code):\n"
            "        return self._clicks.get(code)\n"
        ),
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=6):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Add /stats/<code> endpoint",
    {
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=6):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "@app.route(\"/stats/<code>\")\n"
            "def stats(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    return jsonify({\"url\": url, \"clicks\": store.get_clicks(code)})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Minor cleanup: extract code generation constants",
    {
        "store.py": (
            "CODE_LENGTH = 6\n\n\n"
            "class LinkStore:\n"
            "    def __init__(self):\n"
            "        self._links = {}\n"
            "        self._clicks = {}\n\n"
            "    def save(self, code, url):\n"
            "        self._links[code] = url\n"
            "        self._clicks[code] = 0\n\n"
            "    def get(self, code):\n"
            "        return self._links.get(code)\n\n"
            "    def record_click(self, code):\n"
            "        if code in self._clicks:\n"
            "            self._clicks[code] += 1\n\n"
            "    def get_clicks(self, code):\n"
            "        return self._clicks.get(code)\n"
        ),
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import CODE_LENGTH, LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=CODE_LENGTH):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "@app.route(\"/stats/<code>\")\n"
            "def stats(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    return jsonify({\"url\": url, \"clicks\": store.get_clicks(code)})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Add optional link expiration (ttl_seconds)",
    {
        "store.py": (
            "import time\n\n"
            "CODE_LENGTH = 6\n\n\n"
            "class LinkStore:\n"
            "    def __init__(self):\n"
            "        self._links = {}\n"
            "        self._clicks = {}\n"
            "        self._expires = {}\n\n"
            "    def save(self, code, url, ttl_seconds=None):\n"
            "        self._links[code] = url\n"
            "        self._clicks[code] = 0\n"
            "        self._expires[code] = (\n"
            "            time.time() + ttl_seconds if ttl_seconds is not None else None\n"
            "        )\n\n"
            "    def get(self, code):\n"
            "        return self._links.get(code)\n\n"
            "    def record_click(self, code):\n"
            "        if code in self._clicks:\n"
            "            self._clicks[code] += 1\n\n"
            "    def get_clicks(self, code):\n"
            "        return self._clicks.get(code)\n"
        ),
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import CODE_LENGTH, LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=CODE_LENGTH):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    ttl_seconds = request.json.get(\"ttl_seconds\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url, ttl_seconds=ttl_seconds)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "@app.route(\"/stats/<code>\")\n"
            "def stats(code):\n"
            "    url = store.get(code)\n"
            "    if url is None:\n"
            "        abort(404)\n"
            "    return jsonify({\"url\": url, \"clicks\": store.get_clicks(code)})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Expire links lazily on lookup",
    {
        "store.py": (
            "import time\n\n"
            "CODE_LENGTH = 6\n\n\n"
            "class LinkStore:\n"
            "    def __init__(self):\n"
            "        self._links = {}\n"
            "        self._clicks = {}\n"
            "        self._expires = {}\n\n"
            "    def save(self, code, url, ttl_seconds=None):\n"
            "        self._links[code] = url\n"
            "        self._clicks[code] = 0\n"
            "        self._expires[code] = (\n"
            "            time.time() + ttl_seconds if ttl_seconds is not None else None\n"
            "        )\n\n"
            "    def _is_expired(self, code):\n"
            "        expires_at = self._expires.get(code)\n"
            "        return expires_at is not None and time.time() > expires_at\n\n"
            "    def get(self, code):\n"
            "        if self._is_expired(code):\n"
            "            self._links.pop(code, None)\n"
            "            self._expires.pop(code, None)\n"
            "            self._clicks.pop(code, None)\n"
            "            return None\n"
            "        return self._links.get(code)\n\n"
            "    def record_click(self, code):\n"
            "        if code in self._clicks:\n"
            "            self._clicks[code] += 1\n\n"
            "    def get_clicks(self, code):\n"
            "        return self._clicks.get(code)\n"
        ),
    },
))

# ---------------------------------------------------------------------------
# BUG COMMIT (index 11, the 12th commit): unit-mismatch in expiry clock +
# background cleanup thread + redirect route switched to direct dict access.
# ---------------------------------------------------------------------------
STEPS.append((
    "Add background cleanup thread for expired links (finer-grained clock)",
    {
        "store.py": (
            "import threading\n"
            "import time\n\n"
            "CODE_LENGTH = 6\n"
            "CLEANUP_INTERVAL_SECONDS = 5\n\n\n"
            "class LinkStore:\n"
            "    def __init__(self):\n"
            "        self._links = {}\n"
            "        self._clicks = {}\n"
            "        self._expires = {}\n"
            "        self._start_cleanup_thread()\n\n"
            "    def save(self, code, url, ttl_seconds=None):\n"
            "        self._links[code] = url\n"
            "        self._clicks[code] = 0\n"
            "        self._expires[code] = (\n"
            "            time.time() + ttl_seconds if ttl_seconds is not None else None\n"
            "        )\n\n"
            "    def _is_expired(self, code):\n"
            "        expires_at = self._expires.get(code)\n"
            "        # NOTE: switched the live clock to milliseconds for finer-grained\n"
            "        # cleanup scheduling; expires_at below is still the original\n"
            "        # seconds-based value computed in save().\n"
            "        now_ms = time.time() * 1000\n"
            "        return expires_at is not None and now_ms > expires_at\n\n"
            "    def get(self, code):\n"
            "        # Cleanup thread already purges expired entries, so a hit here\n"
            "        # is assumed live -- go straight to the dict.\n"
            "        return self._links[code]\n\n"
            "    def record_click(self, code):\n"
            "        if code in self._clicks:\n"
            "            self._clicks[code] += 1\n\n"
            "    def get_clicks(self, code):\n"
            "        return self._clicks.get(code)\n\n"
            "    def _cleanup_loop(self):\n"
            "        while True:\n"
            "            for code in list(self._expires.keys()):\n"
            "                if self._is_expired(code):\n"
            "                    self._links.pop(code, None)\n"
            "                    self._expires.pop(code, None)\n"
            "                    self._clicks.pop(code, None)\n"
            "            time.sleep(CLEANUP_INTERVAL_SECONDS)\n\n"
            "    def _start_cleanup_thread(self):\n"
            "        t = threading.Thread(target=self._cleanup_loop, daemon=True)\n"
            "        t.start()\n"
        ),
        "app.py": (
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import CODE_LENGTH, LinkStore\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=CODE_LENGTH):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    ttl_seconds = request.json.get(\"ttl_seconds\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url, ttl_seconds=ttl_seconds)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    url = store.get(code)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "@app.route(\"/stats/<code>\")\n"
            "def stats(code):\n"
            "    url = store.get(code)\n"
            "    return jsonify({\"url\": url, \"clicks\": store.get_clicks(code)})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Add structured logging for redirects",
    {
        "app.py": (
            "import logging\n"
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import CODE_LENGTH, LinkStore\n\n"
            "logging.basicConfig(level=logging.INFO)\n"
            "logger = logging.getLogger(\"shortlink\")\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=CODE_LENGTH):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    ttl_seconds = request.json.get(\"ttl_seconds\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url, ttl_seconds=ttl_seconds)\n"
            "    logger.info(\"shortened url into code=%s\", code)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    logger.info(\"redirect requested for code=%s\", code)\n"
            "    url = store.get(code)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "@app.route(\"/stats/<code>\")\n"
            "def stats(code):\n"
            "    url = store.get(code)\n"
            "    return jsonify({\"url\": url, \"clicks\": store.get_clicks(code)})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

STEPS.append((
    "Add rate limit stub for /shorten (not yet enforced)",
    {
        "ratelimit.py": (
            "# TODO: wire this into /shorten once we pick a backing store\n"
            "# for counters (redis vs in-memory).\n"
            "REQUESTS_PER_MINUTE = 60\n\n\n"
            "def is_allowed(client_id):\n"
            "    return True\n"
        ),
    },
))

STEPS.append((
    "Update README with API docs",
    {
        "README.md": (
            "# ShortLink\n\n"
            "A tiny toy URL shortener used as the substrate for the "
            "incident-response-ai project.\n\n"
            "## API\n\n"
            "- `POST /shorten` `{\"url\": \"...\", \"alias\": \"optional\", "
            "\"ttl_seconds\": optional}` -> `{\"code\": \"...\"}`\n"
            "- `GET /<code>` -> redirects to the original URL\n"
            "- `GET /stats/<code>` -> `{\"url\": \"...\", \"clicks\": N}`\n"
            "- `GET /health` -> `{\"status\": \"ok\"}`\n"
        ),
    },
))

STEPS.append((
    "Add /links/count admin endpoint",
    {
        "app.py": (
            "import logging\n"
            "import random\n"
            "import string\n\n"
            "from flask import Flask, abort, jsonify, redirect, request\n\n"
            "from store import CODE_LENGTH, LinkStore\n\n"
            "logging.basicConfig(level=logging.INFO)\n"
            "logger = logging.getLogger(\"shortlink\")\n\n"
            "app = Flask(__name__)\n"
            "store = LinkStore()\n\n\n"
            "def generate_code(length=CODE_LENGTH):\n"
            "    alphabet = string.ascii_letters + string.digits\n"
            "    return \"\".join(random.choice(alphabet) for _ in range(length))\n\n\n"
            "@app.route(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n\n\n"
            "@app.route(\"/shorten\", methods=[\"POST\"])\n"
            "def shorten():\n"
            "    url = request.json[\"url\"]\n"
            "    if not (url.startswith(\"http://\") or url.startswith(\"https://\")):\n"
            "        return jsonify({\"error\": \"url must start with http:// or https://\"}), 400\n"
            "    alias = request.json.get(\"alias\")\n"
            "    ttl_seconds = request.json.get(\"ttl_seconds\")\n"
            "    code = alias if alias and store.get(alias) is None else generate_code()\n"
            "    store.save(code, url, ttl_seconds=ttl_seconds)\n"
            "    logger.info(\"shortened url into code=%s\", code)\n"
            "    return jsonify({\"code\": code})\n\n\n"
            "@app.route(\"/<code>\")\n"
            "def go(code):\n"
            "    logger.info(\"redirect requested for code=%s\", code)\n"
            "    url = store.get(code)\n"
            "    store.record_click(code)\n"
            "    return redirect(url)\n\n\n"
            "@app.route(\"/stats/<code>\")\n"
            "def stats(code):\n"
            "    url = store.get(code)\n"
            "    return jsonify({\"url\": url, \"clicks\": store.get_clicks(code)})\n\n\n"
            "@app.route(\"/links/count\")\n"
            "def links_count():\n"
            "    return jsonify({\"count\": len(store._links)})\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(port=5000)\n"
        ),
    },
))

assert len(STEPS) == len(OFFSETS_DAYS_AGO), (len(STEPS), len(OFFSETS_DAYS_AGO))


def main():
    if os.path.exists(TOY_APP):
        shutil.rmtree(TOY_APP, onerror=_on_rm_error)
    os.makedirs(TOY_APP)
    run_git(["init", "-b", "main"], cwd=TOY_APP)
    run_git(["config", "user.name", "John Yang"], cwd=TOY_APP)
    run_git(["config", "user.email", "john@example.com"], cwd=TOY_APP)

    deploys = {}
    bug_sha = None
    for i, ((message, files), days_ago) in enumerate(zip(STEPS, OFFSETS_DAYS_AGO)):
        when = NOW - timedelta(days=days_ago, hours=-10)  # ~10am, days_ago days back
        write_files(files)
        sha = commit(message, when)
        deploy_time = when + timedelta(minutes=15)  # deployed shortly after commit
        deploys[sha] = deploy_time.isoformat()
        if i == BUG_COMMIT_INDEX:
            bug_sha = sha
        print(f"[{i:02d}] {sha[:8]}  deploy={deploy_time.isoformat()}  {message}")

    with open(os.path.join(ROOT, "deploys.json"), "w") as f:
        json.dump(deploys, f, indent=2)

    # Kept separate from deploys.json: the AI pipeline (suspect-commit ID, etc.)
    # must never read this file -- it's only for scoring the pipeline's output
    # against the known-correct answer during development/demos.
    ground_truth = {
        "bug_commit_sha": bug_sha,
        "bug_deploy_time": deploys[bug_sha],
        "affected_endpoint": "GET /<code>",
        "description": (
            "Unit mismatch between how link expiry is stored (seconds since "
            "epoch) and how the background cleanup thread compares it "
            "(milliseconds since epoch) causes nearly all links to be purged "
            "within one cleanup cycle (~5s) of creation. The same commit also "
            "switched GET /<code> from store.get() to a direct dict lookup, "
            "so the resulting miss raises an unhandled KeyError (500) instead "
            "of a clean 404."
        ),
    }
    with open(os.path.join(ROOT, "ground_truth.json"), "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\nBug commit SHA: {bug_sha}")
    print(f"Wrote {len(deploys)} deploy records to deploys.json")
    print("Wrote ground_truth.json (dev/demo use only -- not for the pipeline to read)")


if __name__ == "__main__":
    main()
