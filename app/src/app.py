"""Main Flask application.

This module exposes a small demo service that fetches public GitHub profile
metrics and serves a static frontend dashboard. The goal is to provide a
professional, production-minded example that is easy to extend and deploy.

Key features implemented below:
- /           -> serves the frontend dashboard (index.html)
- /healthz    -> simple health endpoint
- /api/profile/<username> -> aggregates public GitHub metrics for a username

Notes for DevOps:
- Honors GITHUB_TOKEN env var for authenticated GitHub API requests to avoid
  strict rate limits in CI or heavy usage.
- Adds simple in-memory TTL cache to reduce repeated API calls on short times.
"""

from flask import Flask, jsonify, send_from_directory, request
import os
import requests
import time
from collections import Counter
from typing import Dict, Any, Optional

# Basic configuration
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Serve static files directly at the application root so the SPA can request
# assets like `/style.css` and `/app.js` without a `/static` prefix. This
# keeps the demo simple and friendly for Netlify/local setups.
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')


class SimpleTTLCache:
    """A tiny thread-unsafe TTL cache for demo purposes.

    Avoids adding dependencies while reducing GitHub API calls during demos.
    For production use a proper cache (Redis, memcached) behind the app.
    """

    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self.store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self.store.get(key)
        if not entry:
            return None
        value, when = entry
        if time.time() - when > self.ttl:
            del self.store[key]
            return None
        return value

    def set(self, key: str, value: Any):
        self.store[key] = (value, time.time())


# Create a session and attach optional auth header for better rate limits.
session = requests.Session()
if GITHUB_TOKEN:
    session.headers.update({"Authorization": f"token {GITHUB_TOKEN}"})
session.headers.update({"User-Agent": "cloud-cicd-platform-demo"})

cache = SimpleTTLCache(ttl_seconds=60)


@app.after_request
def add_cors_and_cache_headers(response):
    # Allow demo frontends to call the API from any origin (safe for demo).
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.route("/")
def index():
    """Serve the static dashboard index file.

    The static folder contains a single-page app that consumes the API below.
    """
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


def _github_get(path: str, params: Dict[str, Any] = None) -> requests.Response:
    """Helper for GitHub GET requests with basic error handling."""
    url = f"{GITHUB_API}{path}"
    resp = session.get(url, params=params or {}, timeout=10)
    resp.raise_for_status()
    return resp


def aggregate_github_profile(username: str) -> Dict[str, Any]:
    """Collect public metrics for a GitHub username.

    This function intentionally favors a small number of API calls. It does
    not request commit lists for every repo to avoid rate limit exhaustion.
    Instead it uses repo metadata (pushed_at) to give activity signals.
    """

    cache_key = f"profile:{username}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 1) Basic user info
    user = _github_get(f"/users/{username}").json()

    # 2) Repos (paginate max 100 first page) - good enough for demos
    repos = _github_get(f"/users/{username}/repos", params={"per_page": 100}).json()

    # Sort repos by most recently updated/pushed (newest first) so the UI
    # shows recent work at the top. Use pushed_at when available, otherwise
    # fall back to updated_at.
    from datetime import datetime

    def repo_time_key(r):
        t = r.get("pushed_at") or r.get("updated_at")
        try:
            return datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ") if t else datetime.min
        except Exception:
            return datetime.min

    repos = sorted(repos, key=repo_time_key, reverse=True)

    # Compute aggregates
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)
    repo_count = len(repos)

    # Language distribution and top repos
    languages = Counter()
    top_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:6]
    for r in repos:
        lang = r.get("language") or "Unknown"
        # Normalize language labels (e.g. uppercase HCL is shown as 'HCL')
        if isinstance(lang, str):
            lang = lang.strip() or "Unknown"
        languages[lang] += 1

    # Recent activity: count repos pushed in last 90 days
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    recent_cutoff = now - timedelta(days=90)
    recent_updates = 0
    for r in repos:
        pushed = r.get("pushed_at")
        if pushed:
            try:
                pushed_dt = datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ")
                if pushed_dt > recent_cutoff:
                    recent_updates += 1
            except Exception:
                # Ignore parsing errors for robustness in demo
                pass

    result = {
        "username": user.get("login"),
        "name": user.get("name"),
        "bio": user.get("bio"),
    # Provide a fallback avatar so the UI always has an image to render
    "avatar_url": user.get("avatar_url") or "https://avatars.githubusercontent.com/u/9919?s=200&v=4",
        "html_url": user.get("html_url"),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", repo_count),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "repo_count": repo_count,
        "top_repos": [
            {
                "name": r.get("name"),
                "html_url": r.get("html_url"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "language": r.get("language"),
            }
            for r in top_repos
        ],
        "languages": dict(languages),
        "recent_repo_updates_90d": recent_updates,
        "fetched_at": time.time(),
    }

    cache.set(cache_key, result)
    return result


@app.route("/api/profile/<username>")
def api_profile(username):
    """Public API endpoint returning aggregated GitHub metrics for a username.

    Returns JSON with basic profile info, aggregates, and small arrays for
    list-like metrics. Errors are translated to user-friendly JSON responses.
    """
    try:
        data = aggregate_github_profile(username)
        return jsonify({"ok": True, "profile": data}), 200
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        # GitHub returns 404 for missing users
        return (
            jsonify({"ok": False, "error": "GitHub API error", "status": status}),
            status,
        )
    except Exception as e:
        # Generic fallback for robustness in demos
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Do not enable debug mode here; the Dockerfile runs the module directly.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)