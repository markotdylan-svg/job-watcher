"""Convert raw API responses from each ATS into one common set of columns.

Common columns: source, source_id, employer, title, location, department,
posted_date, url. A field the ATS does not provide is left as "".
"""

from datetime import datetime, timezone

COMMON_FIELDS = ["source", "source_id", "employer", "title", "location", "department", "posted_date", "url"]


def clean(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())  # collapse whitespace and newlines


def utc_date_from_iso(value) -> str:
    """'2026-11-12T23:52:40-05:00' -> '2026-11-13' (UTC). Empty on missing/invalid input."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def utc_date_from_ms(value) -> str:
    if value in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OverflowError, OSError):
        return ""


def _row(raw, source_id, title, location, department, posted_date, url) -> dict:
    return {
        "source": raw["source"],
        "source_id": clean(source_id),
        "employer": raw["employer"],
        "title": clean(title),
        "location": clean(location),
        "department": clean(department),
        "posted_date": posted_date,
        "url": clean(url),
    }


def convert_greenhouse(raw: dict) -> list[dict]:
    rows = []
    for page in raw["responses"]:
        for j in page.get("jobs", []):
            rows.append(_row(
                raw, j.get("id"), j.get("title"),
                (j.get("location") or {}).get("name"),
                "",  # departments are only returned with ?content=true, which we do not request
                utc_date_from_iso(j.get("first_published")),
                j.get("absolute_url"),
            ))
    return rows


def convert_lever(raw: dict) -> list[dict]:
    rows = []
    for page in raw["responses"]:
        for j in page:
            cat = j.get("categories") or {}
            rows.append(_row(
                raw, j.get("id"), j.get("text"), cat.get("location"),
                cat.get("department") or cat.get("team"),
                utc_date_from_ms(j.get("createdAt")),
                j.get("hostedUrl"),
            ))
    return rows


def convert_ashby(raw: dict) -> list[dict]:
    rows = []
    for page in raw["responses"]:
        for j in page.get("jobs", []):
            rows.append(_row(
                raw, j.get("id"), j.get("title"), j.get("location"), j.get("department"),
                utc_date_from_iso(j.get("publishedAt")),
                j.get("jobUrl"),
            ))
    return rows


def convert_smartrecruiters(raw: dict) -> list[dict]:
    rows = []
    for page in raw["responses"]:
        for j in page.get("content", []):
            loc = j.get("location") or {}
            location = loc.get("fullLocation") or ", ".join(
                p for p in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if p
            )
            company = (j.get("company") or {}).get("identifier", "")
            rows.append(_row(
                raw, j.get("id"), j.get("name"), location.replace(", ,", ","),
                (j.get("department") or {}).get("label"),
                utc_date_from_iso(j.get("releasedDate")),
                f"https://jobs.smartrecruiters.com/{company}/{j.get('id')}",
            ))
    return rows


def workday_id(external_path: str) -> str:
    """'/job/Riverwoods-IL/Security-Engineer-4_R1002814-1' -> 'R1002814-1'."""
    last = (external_path or "").rstrip("/").split("/")[-1]
    return last.rsplit("_", 1)[-1] if "_" in last else last


def convert_workday(raw: dict) -> list[dict]:
    rows = []
    req_url = raw["requests"][0]["url"]  # https://<host>/wday/cxs/<tenant>/<site>/jobs
    host = req_url.split("/")[2]
    site = req_url.rstrip("/").split("/")[-2]
    for page in raw["responses"]:
        for j in page.get("jobPostings", []):
            path = j.get("externalPath") or ""
            bullets = j.get("bulletFields") or []
            source_id = workday_id(path) or (clean(bullets[0]) if bullets else "")
            rows.append(_row(
                raw, source_id, j.get("title"), j.get("locationsText"),
                "",  # the list API does not return a department
                "",  # Workday only gives a relative date ("Posted 3 Days Ago")
                f"https://{host}/{site}{path}" if path else f"https://{host}/{site}",
            ))
    return rows


CONVERTERS = {
    "greenhouse": convert_greenhouse,
    "lever": convert_lever,
    "ashby": convert_ashby,
    "smartrecruiters": convert_smartrecruiters,
    "workday": convert_workday,
}


def convert(raw: dict) -> list[dict]:
    """Convert one raw file into common rows. Duplicate IDs within a file keep the first."""
    rows, seen = [], set()
    for row in CONVERTERS[raw["ats"]](raw):
        if not row["source_id"] or row["source_id"] in seen:
            continue
        seen.add(row["source_id"])
        rows.append(row)
    return rows
