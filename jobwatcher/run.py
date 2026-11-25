"""The daily pipeline. GitHub Actions runs this once a day:

    uv run python -m jobwatcher.run

1. Fetch every source and save data/raw/<date>/<source>.json.gz (a failed
   source writes no file; every result is logged in data/runs/<date>.json).
2. Rebuild data/history.csv from all raw files.
3. Write data/status.json.
4. Open or update the issue for the date and close the previous one.
(5. The workflow commits the data files.)

A second run on the same UTC date replaces that date's raw files.
"""

import argparse
import json
import shutil
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .build import build_history, write_history
from .fetch import fetch_source, write_raw
from .issue import publish_from_env
from .normalize import convert
from .sources import SOURCES, Source
from .status import make_status, write_status


def fetch_one(src: Source) -> tuple[Source, dict | None, dict]:
    t0 = time.monotonic()
    try:
        raw = fetch_source(src)
        count = len(convert(raw))
        result = {"ok": True, "count": count, "error": ""}
    except Exception as e:  # one source failing must not stop the run
        raw = None
        result = {"ok": False, "count": 0, "error": f"{type(e).__name__}: {e}"[:300]}
    result.update(name=src.name, employer=src.employer, ats=src.ats, seconds=round(time.monotonic() - t0, 1))
    return src, raw, result


def fetch_all(sources: list[Source], day_dir: Path) -> list[dict]:
    if day_dir.exists():
        shutil.rmtree(day_dir)  # a second run the same day replaces that day's raw files
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for src, raw, result in pool.map(fetch_one, sources):
            if raw is not None:
                write_raw(raw, day_dir / f"{src.name}.json.gz")
            flag = "ok  " if result["ok"] else "FAIL"
            print(f"{flag} {src.name:12} {result['count']:6} postings {result['seconds']:7.1f}s {result['error']}", flush=True)
            results.append(result)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the daily Job Watcher pipeline")
    ap.add_argument("--data", default="data")
    ap.add_argument("--no-issue", action="store_true", help="do not open the GitHub issue")
    ap.add_argument("--only", nargs="*", help="fetch only these sources (for local testing)")
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    run_date, run_time = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = Path(args.data)
    sources = [s for s in SOURCES if not args.only or s.name in args.only]

    results = fetch_all(sources, data / "raw" / run_date)
    runs_dir = data / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    with open(runs_dir / f"{run_date}.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump({"run_time": run_time, "run_date": run_date, "sources": results}, f, indent=2)
        f.write("\n")

    history = build_history(data / "raw")
    write_history(history, data / "history.csv")
    status = make_status(history, data / "raw", run_time, run_date, results)
    write_status(status, data / "status.json")
    ok = sum(r["ok"] for r in results)
    print(f"{run_date}: {ok}/{len(results)} sources ok, {status['open']} open, "
          f"{status['new_today']} new, {status['removed_today']} removed")

    if not args.no_issue:
        try:
            number = publish_from_env(history, status)
            if number:
                print(f"issue #{number} updated for {run_date}")
        except Exception:
            # the data still gets committed; flag the problem in the Actions log
            traceback.print_exc()
            print("::warning::could not open the daily issue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
