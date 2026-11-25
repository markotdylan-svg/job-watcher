"""The run survives failing sources and keeps Workday within its time budget."""

import jobwatcher.run as run
from jobwatcher.fetch import read_raw
from jobwatcher.sources import Source


def test_failed_source_writes_no_raw_file_and_is_recorded(tmp_path, monkeypatch):
    good = Source("good", "Good", "greenhouse", {"board": "good"})
    bad = Source("bad", "Bad", "greenhouse", {"board": "bad"})

    def fake_fetch(src, **kw):
        if src.name == "bad":
            raise RuntimeError("HTTP Error 429")
        return {"source": src.name, "employer": src.employer, "ats": "greenhouse", "requests": [{"url": "x"}],
                "responses": [{"jobs": [{"id": 1, "title": "Credit Analyst", "location": {"name": "NY"},
                                          "absolute_url": "u"}]}]}

    monkeypatch.setattr(run, "fetch_source", fake_fetch)
    day = tmp_path / "raw" / "2026-11-25"
    (day).mkdir(parents=True)
    (day / "stale.json.gz").write_bytes(b"old")  # a same-day rerun replaces the day's files
    results = run.fetch_all([good, bad], day)
    assert [r["ok"] for r in results] == [True, False]
    assert results[0]["count"] == 1 and "429" in results[1]["error"]
    assert sorted(p.name for p in day.iterdir()) == ["good.json.gz"]
    assert read_raw(day / "good.json.gz")["source"] == "good"


def test_workday_budget_skips_remaining_boards(monkeypatch):
    calls = []

    def fake_one(src, **kw):
        calls.append((src.name, kw["budget_seconds"]))
        return src, None, {"ok": False, "count": 0, "error": "slow", "name": src.name}

    monkeypatch.setattr(run, "fetch_one", fake_one)
    boards = [Source(f"wd{i}", f"WD{i}", "workday") for i in range(3)]
    out = run.fetch_serially(boards, total_budget=30)  # less than a minute: nothing gets a turn
    assert calls == []
    assert all(r["error"].startswith("skipped") for _, _, r in out)

    out = run.fetch_serially(boards, total_budget=3600)
    assert [name for name, _ in calls] == ["wd0", "wd1", "wd2"]
    assert all(b <= run.WORKDAY_BOARD_BUDGET for _, b in calls)
