"""Write data/status.json, which describes the latest run."""

import json
from pathlib import Path

from .build import raw_days


def make_status(history: list[dict], raw_dir: Path, run_time: str, run_date: str, results: list[dict]) -> dict:
    days = raw_days(raw_dir)
    return {
        "run_time": run_time,
        "run_date": run_date,
        "first_run_date": days[0][0] if days else None,
        "days_with_success": len(days),
        "open": sum(r["status"] == "open" for r in history),
        "new_today": sum(r["first_seen"] == run_date and not r["first_run"] for r in history),
        "removed_today": sum(r["removed_date"] == run_date for r in history),
        "sources": [
            {
                "name": r["name"],
                "employer": r["employer"],
                "ats": r["ats"],
                "ok": r["ok"],
                "count": r["count"],
                "error": r.get("error", ""),
            }
            for r in results
        ],
    }


def write_status(status: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
        f.write("\n")
