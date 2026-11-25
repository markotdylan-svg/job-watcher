"""Call each source's job board API and save what it returns.

Every raw file is a gzip-compressed JSON object:

    {"source": ..., "employer": ..., "ats": ..., "fetched_at": ...,
     "requests": [...], "responses": [...]}

`responses` holds every JSON page the API returned, unchanged. Boards that page
their results (Workday, SmartRecruiters) have one entry per page. A fetch that
does not complete raises an exception, so a partial board is never saved.
"""

import gzip
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .sources import Source

USER_AGENT = "Mozilla/5.0 (compatible; job-watcher/1.0; class project)"
TIMEOUT = 45
RETRY_CODES = {429, 500, 502, 503, 504}


def http_json(url: str, body: dict | None = None, retries: int = 6) -> object:
    """GET (or POST when `body` is given) a URL and parse the JSON reply.

    Retries rate-limit and server errors with exponential backoff.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code not in RETRY_CODES:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
        time.sleep(min(60, 2 ** attempt + 1))
    raise RuntimeError(f"gave up after {retries} attempts: {last_err}")


def fetch_greenhouse(src: Source):
    url = f"https://boards-api.greenhouse.io/v1/boards/{src.config['board']}/jobs"
    resp = http_json(url)
    if not isinstance(resp, dict) or "jobs" not in resp:
        raise ValueError("unexpected Greenhouse response")
    return [{"url": url}], [resp]


def fetch_lever(src: Source):
    url = f"https://api.lever.co/v0/postings/{src.config['site']}?mode=json"
    resp = http_json(url)
    if not isinstance(resp, list):
        raise ValueError("unexpected Lever response")
    return [{"url": url}], [resp]


def fetch_ashby(src: Source):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{src.config['board']}"
    resp = http_json(url)
    if not isinstance(resp, dict) or "jobs" not in resp:
        raise ValueError("unexpected Ashby response")
    return [{"url": url}], [resp]


def fetch_smartrecruiters(src: Source):
    company = src.config["company"]
    requests, pages, offset, limit = [], [], 0, 100
    while True:
        url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings?limit={limit}&offset={offset}"
        resp = http_json(url)
        if not isinstance(resp, dict) or "content" not in resp:
            raise ValueError("unexpected SmartRecruiters response")
        requests.append({"url": url})
        pages.append(resp)
        offset += limit
        if not resp["content"] or offset >= resp.get("totalFound", 0):
            break
        time.sleep(0.3)
    return requests, pages


def fetch_workday(src: Source, delay: float = 0.6, budget_seconds: float = 900):
    c = src.config
    url = f"https://{c['host']}/wday/cxs/{c['tenant']}/{c['site']}/jobs"
    requests, pages, offset, limit, total = [], [], 0, 20, None
    deadline = time.monotonic() + budget_seconds
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(f"Workday board not finished after {budget_seconds:.0f}s (offset {offset} of {total})")
        body = {"limit": limit, "offset": offset, "searchText": src.search_text, "appliedFacets": {}}
        resp = http_json(url, body)
        if not isinstance(resp, dict) or "jobPostings" not in resp:
            raise ValueError("unexpected Workday response")
        if total is None:
            total = resp.get("total", 0)  # Workday only reports the total on the first page
        requests.append({"url": url, "body": body})
        pages.append(resp)
        offset += limit
        if not resp["jobPostings"] or offset >= total:
            break
        time.sleep(delay)
    return requests, pages


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
}


def fetch_source(src: Source) -> dict:
    """Fetch one source and return the raw record that gets saved to disk."""
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    requests, responses = FETCHERS[src.ats](src)
    return {
        "source": src.name,
        "employer": src.employer,
        "ats": src.ats,
        "search_text": src.search_text,
        "fetched_at": fetched_at,
        "requests": requests,
        "responses": responses,
    }


def write_raw(raw: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 keeps the gzip header free of timestamps
    with open(path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
            gz.write(json.dumps(raw, ensure_ascii=False).encode("utf-8"))


def read_raw(path: Path) -> dict:
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))
