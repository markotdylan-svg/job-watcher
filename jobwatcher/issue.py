"""Open (or update) the daily GitHub Issue and close the previous day's issue.

The issue is titled with the run date (YYYY-MM-DD) and lists every new and every
removed posting of that run, each with a link. If the list does not fit in one
issue body (GitHub allows 65,536 characters), the rest is posted as comments.
A second run on the same day edits that day's issue instead of opening another.
"""

import json
import os
import re
import urllib.request

API = "https://api.github.com"
MAX_BODY = 60000
CONT_MARKER = "<!-- job-watcher:continuation -->"
DATE_TITLE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _line(r: dict) -> str:
    title = r["title"].replace("[", "(").replace("]", ")") or "(untitled)"
    loc = f" · {r['location']}" if r["location"] else ""
    return f"- [{title}]({r['url']}) — {r['employer']}{loc}"


def _section(heading: str, rows: list[dict]) -> list[str]:
    role = [r for r in rows if r["in_role"]]
    other = [r for r in rows if not r["in_role"]]
    key = lambda r: (r["employer"], r["title"], r["posting_id"])
    out = [f"## {heading} ({len(rows)})", ""]
    if not rows:
        return out + ["None.", ""]
    out += [f"### Credit analyst roles ({len(role)})", ""]
    out += [_line(r) for r in sorted(role, key=key)] or ["None."]
    out += ["", f"### All other postings ({len(other)})", ""]
    out += [_line(r) for r in sorted(other, key=key)] or ["None."]
    return out + [""]


def issue_lines(history: list[dict], status: dict, site_url: str = "") -> list[str]:
    date = status["run_date"]
    new = [r for r in history if r["first_seen"] == date and not r["first_run"]]
    removed = [r for r in history if r["removed_date"] == date]
    baseline = [r for r in history if r["first_seen"] == date and r["first_run"]]
    failed = [s["name"] for s in status["sources"] if not s["ok"]]
    ok = len(status["sources"]) - len(failed)
    lines = [
        f"Job Watcher run at {status['run_time']}.",
        "",
        f"- Sources OK: {ok} of {len(status['sources'])}" + (f" (failed: {', '.join(failed)})" if failed else ""),
        f"- Open postings: {status['open']}",
        f"- New today: {status['new_today']}",
        f"- Removed today: {status['removed_today']}",
    ]
    if baseline:
        lines.append(f"- First-run postings recorded as baseline (not counted as new): {len(baseline)}")
    if site_url:
        lines.append(f"- Site: {site_url}")
    lines.append("")
    return lines + _section("New postings", new) + _section("Removed postings", removed)


def chunk(lines: list[str], limit: int = MAX_BODY) -> list[str]:
    chunks, cur, size = [], [], 0
    for line in lines:
        if cur and size + len(line) + 1 > limit:
            chunks.append("\n".join(cur))
            cur, size = [CONT_MARKER, "_(continued)_", ""], 40
        cur.append(line)
        size += len(line) + 1
    chunks.append("\n".join(cur))
    return chunks


class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo, self.token = repo, token

    def call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            f"{API}/repos/{self.repo}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "job-watcher",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read()
            return json.loads(text) if text else None

    def date_issues(self, state: str) -> list[dict]:
        out, page = [], 1
        while True:
            items = self.call("GET", f"/issues?state={state}&per_page=100&page={page}")
            out += [i for i in items if "pull_request" not in i and DATE_TITLE.match(i["title"])]
            if len(items) < 100:
                return out
            page += 1


def publish_issue(history: list[dict], status: dict, repo: str, token: str, site_url: str = "") -> int:
    gh = GitHub(repo, token)
    date = status["run_date"]
    chunks = chunk(issue_lines(history, status, site_url))

    existing = [i for i in gh.date_issues("all") if i["title"] == date]
    if existing:
        number = existing[0]["number"]
        gh.call("PATCH", f"/issues/{number}", {"body": chunks[0], "state": "open"})
        for c in gh.call("GET", f"/issues/{number}/comments?per_page=100"):
            if c["body"].startswith(CONT_MARKER):
                gh.call("DELETE", f"/issues/comments/{c['id']}")
    else:
        number = gh.call("POST", "/issues", {"title": date, "body": chunks[0]})["number"]
    for extra in chunks[1:]:
        gh.call("POST", f"/issues/{number}/comments", {"body": extra})

    for i in gh.date_issues("open"):
        if i["number"] != number and i["title"] < date:
            gh.call("PATCH", f"/issues/{i['number']}", {"state": "closed", "state_reason": "completed"})
    return number


def publish_from_env(history: list[dict], status: dict) -> int | None:
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("GITHUB_REPOSITORY/GITHUB_TOKEN not set; skipping the issue")
        return None
    owner, name = repo.split("/")
    site = f"https://{owner.lower()}.github.io/{name}/"
    return publish_issue(history, status, repo, token, site)
