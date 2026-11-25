"""status.json counts and the daily issue body."""

from jobwatcher.build import build_history
from jobwatcher.fetch import write_raw
from jobwatcher.issue import CONT_MARKER, chunk, issue_lines
from jobwatcher.status import make_status


def save(tmp_path, date, source, ids):
    raw = {"source": source, "employer": source.title(), "ats": "greenhouse", "requests": [{"url": "x"}],
           "responses": [{"jobs": [{"id": i, "title": f"Credit Analyst {i}", "location": {"name": "NY"},
                                     "absolute_url": f"https://x/{i}"} for i in ids]}]}
    write_raw(raw, tmp_path / "raw" / date / f"{source}.json.gz")


def test_status_counts(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1, 2, 3])
    save(tmp_path, "2026-11-26", "acme", [1, 2, 4, 5])
    (tmp_path / "raw" / "2026-11-24").mkdir()  # an empty day does not count
    history = build_history(tmp_path / "raw")
    results = [{"name": "acme", "employer": "Acme", "ats": "greenhouse", "ok": True, "count": 4},
               {"name": "beta", "employer": "Beta", "ats": "lever", "ok": False, "count": 0, "error": "boom"}]
    s = make_status(history, tmp_path / "raw", "2026-11-26T13:00:00Z", "2026-11-26", results)
    assert s["first_run_date"] == "2026-11-25"
    assert s["days_with_success"] == 2
    assert s["open"] == 4
    assert s["new_today"] == 2
    assert s["removed_today"] == 1
    assert s["sources"][1] == {"name": "beta", "employer": "Beta", "ats": "lever", "ok": False, "count": 0,
                               "error": "boom"}


def test_first_run_postings_are_not_new(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1, 2])
    history = build_history(tmp_path / "raw")
    s = make_status(history, tmp_path / "raw", "2026-11-25T13:00:00Z", "2026-11-25", [])
    assert s["new_today"] == 0 and s["open"] == 2


def test_issue_lists_new_and_removed_with_links(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1, 2])
    save(tmp_path, "2026-11-26", "acme", [1, 3])
    history = build_history(tmp_path / "raw")
    s = make_status(history, tmp_path / "raw", "2026-11-26T13:00:00Z", "2026-11-26",
                    [{"name": "acme", "employer": "Acme", "ats": "greenhouse", "ok": True, "count": 2}])
    body = "\n".join(issue_lines(history, s))
    assert "## New postings (1)" in body
    assert "- [Credit Analyst 3](https://x/3) — Acme · NY" in body
    assert "## Removed postings (1)" in body
    assert "- [Credit Analyst 2](https://x/2) — Acme · NY" in body


def test_issue_body_on_a_day_with_no_changes(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1])
    save(tmp_path, "2026-11-26", "acme", [1])
    history = build_history(tmp_path / "raw")
    s = make_status(history, tmp_path / "raw", "2026-11-26T13:00:00Z", "2026-11-26", [])
    body = "\n".join(issue_lines(history, s))
    assert "## New postings (0)" in body and "## Removed postings (0)" in body


def test_long_issue_is_split_without_losing_lines():
    lines = [f"- line {i} " + "x" * 80 for i in range(3000)]
    parts = chunk(lines, limit=60000)
    assert len(parts) > 1
    assert all(len(p) <= 60000 for p in parts)
    assert all(p.startswith(CONT_MARKER) for p in parts[1:])
    joined = "\n".join(parts)
    assert all(line in joined for line in lines)
