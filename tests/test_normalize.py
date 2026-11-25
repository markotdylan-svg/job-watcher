"""Each ATS's raw response converts to the common columns."""

from jobwatcher.normalize import COMMON_FIELDS, convert, utc_date_from_iso, workday_id


def raw(ats, responses, source="acme", employer="Acme", requests=None):
    return {"source": source, "employer": employer, "ats": ats, "requests": requests or [{"url": "x"}],
            "responses": responses}


def test_greenhouse():
    r = raw("greenhouse", [{"jobs": [{
        "id": 8200888003, "title": "  Credit   Analyst ", "location": {"name": "New York, NY"},
        "absolute_url": "https://boards.greenhouse.io/acme/jobs/8200888003",
        "first_published": "2026-11-12T21:52:40-05:00",
    }], "meta": {"total": 1}}])
    rows = convert(r)
    assert rows == [{
        "source": "acme", "source_id": "8200888003", "employer": "Acme", "title": "Credit Analyst",
        "location": "New York, NY", "department": "", "posted_date": "2026-11-13",  # converted to UTC
        "url": "https://boards.greenhouse.io/acme/jobs/8200888003",
    }]
    assert list(rows[0]) == COMMON_FIELDS


def test_lever():
    r = raw("lever", [[{
        "id": "26d4-abc", "text": "Loan Review Analyst",
        "categories": {"location": "Boston, MA", "department": "Risk", "team": "Credit"},
        "createdAt": 1786650451274, "hostedUrl": "https://jobs.lever.co/acme/26d4-abc",
    }]])
    assert convert(r) == [{
        "source": "acme", "source_id": "26d4-abc", "employer": "Acme", "title": "Loan Review Analyst",
        "location": "Boston, MA", "department": "Risk", "posted_date": "2026-08-13",
        "url": "https://jobs.lever.co/acme/26d4-abc",
    }]


def test_ashby():
    r = raw("ashby", [{"jobs": [{
        "id": "3441-f8d", "title": "Credit Underwriter", "department": "Credit", "location": "Remote (US)",
        "publishedAt": "2026-04-07T17:12:35.753+00:00", "jobUrl": "https://jobs.ashbyhq.com/acme/3441-f8d",
    }]}])
    assert convert(r) == [{
        "source": "acme", "source_id": "3441-f8d", "employer": "Acme", "title": "Credit Underwriter",
        "location": "Remote (US)", "department": "Credit", "posted_date": "2026-04-07",
        "url": "https://jobs.ashbyhq.com/acme/3441-f8d",
    }]


def test_smartrecruiters_pages_are_combined():
    page1 = {"offset": 0, "limit": 1, "totalFound": 2, "content": [{
        "id": "7440001", "name": "Credit Risk Analyst", "company": {"identifier": "Acme"},
        "location": {"city": "Costa Mesa", "region": "CA", "country": "us", "fullLocation": "Costa Mesa, CA, United States"},
        "department": {"label": "Risk"}, "releasedDate": "2026-11-25T18:40:39.014Z",
    }]}
    page2 = {"offset": 1, "limit": 1, "totalFound": 2, "content": [{
        "id": "7440002", "name": "Analyst", "company": {"identifier": "Acme"},
        "location": {"city": "London", "country": "gb"}, "releasedDate": None,
    }]}
    rows = convert(raw("smartrecruiters", [page1, page2]))
    assert rows[0] == {
        "source": "acme", "source_id": "7440001", "employer": "Acme", "title": "Credit Risk Analyst",
        "location": "Costa Mesa, CA, United States", "department": "Risk", "posted_date": "2026-11-25",
        "url": "https://jobs.smartrecruiters.com/Acme/7440001",
    }
    assert rows[1]["location"] == "London, GB"
    assert rows[1]["department"] == "" and rows[1]["posted_date"] == ""


def test_workday():
    url = "https://capitalone.wd12.myworkdayjobs.com/wday/cxs/capitalone/Capital_One/jobs"
    page = {"total": 2, "jobPostings": [
        {"title": "Senior Credit Analyst", "externalPath": "/job/McLean-VA/Senior-Credit-Analyst_R1002814-1",
         "locationsText": "McLean, VA", "postedOn": "Posted Today", "bulletFields": ["R1002814"]},
        {"title": "Teller", "locationsText": "2 Locations", "bulletFields": ["R999"]},  # no externalPath
    ]}
    rows = convert(raw("workday", [page], requests=[{"url": url, "body": {}}]))
    assert rows[0] == {
        "source": "acme", "source_id": "R1002814-1", "employer": "Acme", "title": "Senior Credit Analyst",
        "location": "McLean, VA", "department": "", "posted_date": "",
        "url": "https://capitalone.wd12.myworkdayjobs.com/Capital_One/job/McLean-VA/Senior-Credit-Analyst_R1002814-1",
    }
    assert rows[1]["source_id"] == "R999"
    assert rows[1]["url"] == "https://capitalone.wd12.myworkdayjobs.com/Capital_One"


def test_duplicate_ids_in_one_file_are_kept_once():
    job = {"id": 1, "title": "A", "location": {"name": "X"}, "absolute_url": "u"}
    assert len(convert(raw("greenhouse", [{"jobs": [job, dict(job)]}]))) == 1


def test_helpers():
    assert workday_id("/job/X/Title-With_Underscore_R123-2") == "R123-2"
    assert workday_id("") == ""
    assert utc_date_from_iso("2026-01-01T23:30:00-02:00") == "2026-01-02"
    assert utc_date_from_iso("not a date") == ""
    assert utc_date_from_iso(None) == ""
