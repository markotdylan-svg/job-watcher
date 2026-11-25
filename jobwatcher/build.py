"""Build data/history.csv from the raw files alone.

    uv run python -m jobwatcher.build

The build reads data/raw/<date>/<source>.json.gz day by day, in date order, and
replays the history from scratch, so running it again gives the same file and a
change to a rule (for example the title rule) applies to every day.

For each day and each source that has a raw file that day:
  * a posting seen for the first time gets that day as first_seen
    (and first_run = true if this is the source's first raw file);
  * every posting the source lists gets that day as last_seen, and its
    descriptive fields are refreshed to that day's values;
  * a removed posting that is listed again becomes open, its removed_date is
    cleared, and its first_seen is kept;
  * an open posting of that source that is no longer listed becomes removed
    with that day as removed_date.
A source with no raw file on a day (a failed fetch) changes nothing that day.
"""

import argparse
import csv
import re
from pathlib import Path

from .fetch import read_raw
from .normalize import COMMON_FIELDS, convert
from .rules import in_role

HISTORY_FIELDS = [
    "posting_id", "source", "source_id", "employer", "title", "location", "department",
    "posted_date", "url", "in_role", "first_run", "first_seen", "last_seen", "status", "removed_date",
]
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def raw_days(raw_dir: Path) -> list[tuple[str, list[Path]]]:
    """[(date, [raw files sorted by name]), ...] in date order, skipping empty days."""
    days = []
    if not raw_dir.exists():
        return days
    for d in sorted(p for p in raw_dir.iterdir() if p.is_dir() and DATE_DIR.match(p.name)):
        files = sorted(d.glob("*.json.gz"))
        if files:
            days.append((d.name, files))
    return days


def apply_day(history: dict, date: str, source: str, postings: list[dict], is_first_file: bool) -> None:
    """Update `history` (posting_id -> row) with one source's postings on one day."""
    listed = set()
    for p in postings:
        pid = f"{source}:{p['source_id']}"
        listed.add(pid)
        row = history.get(pid)
        if row is None:
            row = {"posting_id": pid, "first_run": is_first_file, "first_seen": date}
            history[pid] = row
        row.update({k: p[k] for k in COMMON_FIELDS})
        row["source"] = source
        row["last_seen"] = date
        row["status"] = "open"
        row["removed_date"] = ""
    for pid, row in history.items():
        if row["source"] == source and row["status"] == "open" and pid not in listed:
            row["status"] = "removed"
            row["removed_date"] = date


def build_history(raw_dir: Path) -> list[dict]:
    history: dict[str, dict] = {}
    seen_sources: set[str] = set()
    for date, files in raw_days(raw_dir):
        for path in files:
            raw = read_raw(path)
            source = raw["source"]
            is_first_file = source not in seen_sources
            seen_sources.add(source)
            apply_day(history, date, source, convert(raw), is_first_file)
    rows = []
    for pid in sorted(history):
        row = dict(history[pid])
        row["in_role"] = in_role(row["title"])
        rows.append(row)
    return rows


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def write_history(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HISTORY_FIELDS)
        for row in rows:
            w.writerow([_fmt(row.get(k)) for k in HISTORY_FIELDS])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Build data/history.csv from data/raw")
    ap.add_argument("--data", default="data", help="data directory (default: data)")
    args = ap.parse_args(argv)
    data = Path(args.data)
    rows = build_history(data / "raw")
    write_history(rows, data / "history.csv")
    print(f"wrote {data / 'history.csv'}: {len(rows)} postings, "
          f"{sum(r['status'] == 'open' for r in rows)} open")


if __name__ == "__main__":
    main()
