"""first_seen, last_seen, removed and reopened logic, and a reproducible build."""

from jobwatcher.build import apply_day, build_history, write_history
from jobwatcher.fetch import write_raw


def posting(i, title="Credit Analyst"):
    return {"source": "acme", "source_id": str(i), "employer": "Acme", "title": title, "location": "NY",
            "department": "", "posted_date": "", "url": f"https://x/{i}"}


def gh_raw(source, ids, title="Credit Analyst"):
    return {"source": source, "employer": source.title(), "ats": "greenhouse", "requests": [{"url": "x"}],
            "responses": [{"jobs": [{"id": i, "title": title, "location": {"name": "NY"},
                                      "absolute_url": f"https://x/{source}/{i}"} for i in ids]}]}


def save(tmp_path, date, source, ids, **kw):
    write_raw(gh_raw(source, ids, **kw), tmp_path / "raw" / date / f"{source}.json.gz")


def by_id(rows):
    return {r["posting_id"]: r for r in rows}


def test_first_seen_and_first_run():
    h = {}
    apply_day(h, "2026-11-25", "acme", [posting(1), posting(2)], is_first_file=True)
    apply_day(h, "2026-11-26", "acme", [posting(1), posting(2), posting(3)], is_first_file=False)
    assert h["acme:1"]["first_seen"] == "2026-11-25" and h["acme:1"]["first_run"] is True
    assert h["acme:3"]["first_seen"] == "2026-11-26" and h["acme:3"]["first_run"] is False
    assert h["acme:1"]["last_seen"] == "2026-11-26"


def test_removed_when_source_no_longer_lists_it():
    h = {}
    apply_day(h, "2026-11-25", "acme", [posting(1), posting(2)], True)
    apply_day(h, "2026-11-26", "acme", [posting(1)], False)
    assert h["acme:2"]["status"] == "removed"
    assert h["acme:2"]["removed_date"] == "2026-11-26"
    assert h["acme:2"]["last_seen"] == "2026-11-25"
    assert h["acme:1"]["status"] == "open" and h["acme:1"]["removed_date"] == ""


def test_removed_posting_reopens_and_keeps_first_seen():
    h = {}
    apply_day(h, "2026-11-25", "acme", [posting(1)], True)
    apply_day(h, "2026-11-26", "acme", [], False)
    apply_day(h, "2026-11-28", "acme", [posting(1, title="Senior Credit Analyst")], False)
    row = h["acme:1"]
    assert row["status"] == "open" and row["removed_date"] == ""
    assert row["first_seen"] == "2026-11-25" and row["last_seen"] == "2026-11-28"
    assert row["title"] == "Senior Credit Analyst"  # fields refresh to the latest listing


def test_other_sources_are_untouched():
    h = {}
    apply_day(h, "2026-11-25", "acme", [posting(1)], True)
    other = dict(posting(9), source="beta")
    apply_day(h, "2026-11-25", "beta", [other], True)
    apply_day(h, "2026-11-26", "beta", [], False)
    assert h["acme:1"]["status"] == "open"
    assert h["beta:9"]["status"] == "removed"


def test_failed_source_day_changes_nothing(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1, 2])
    save(tmp_path, "2026-11-25", "beta", [7])
    save(tmp_path, "2026-11-26", "beta", [7])  # acme failed on the 26th: no raw file
    save(tmp_path, "2026-11-27", "acme", [1])
    rows = by_id(build_history(tmp_path / "raw"))
    assert rows["acme:2"]["removed_date"] == "2026-11-27"  # not the 26th
    assert rows["acme:1"]["last_seen"] == "2026-11-27"
    assert rows["beta:7"]["last_seen"] == "2026-11-26"
    assert rows["beta:7"]["status"] == "open"  # beta had no file on the 27th


def test_first_run_is_per_source(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1])
    save(tmp_path, "2026-11-26", "acme", [1, 2])
    save(tmp_path, "2026-11-26", "beta", [5])  # beta's first file is on day 2
    rows = by_id(build_history(tmp_path / "raw"))
    assert rows["acme:1"]["first_run"] is True
    assert rows["acme:2"]["first_run"] is False
    assert rows["beta:5"]["first_run"] is True


def test_rows_sorted_and_in_role(tmp_path):
    save(tmp_path, "2026-11-25", "zeta", [3], title="Teller")
    save(tmp_path, "2026-11-25", "acme", [20, 3])
    rows = build_history(tmp_path / "raw")
    assert [r["posting_id"] for r in rows] == ["acme:20", "acme:3", "zeta:3"]
    assert [r["in_role"] for r in rows] == [True, True, False]


def test_build_is_reproducible(tmp_path):
    save(tmp_path, "2026-11-25", "acme", [1, 2, 3])
    save(tmp_path, "2026-11-26", "acme", [2, 3, 4])
    save(tmp_path, "2026-11-27", "acme", [1, 4])
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    write_history(build_history(tmp_path / "raw"), a)
    write_history(build_history(tmp_path / "raw"), b)
    assert a.read_bytes() == b.read_bytes()
    text = a.read_text(encoding="utf-8").splitlines()
    assert text[0].startswith("posting_id,source,source_id,employer,title")
    assert "acme:1,acme,1,Acme,Credit Analyst,NY,,,https://x/acme/1,true,true,2026-11-25,2026-11-27,open," in text
    assert "acme:3,acme,3,Acme,Credit Analyst,NY,,,https://x/acme/3,true,true,2026-11-25,2026-11-26,removed,2026-11-27" in text
