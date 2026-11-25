# Job Watcher — credit analyst roles

[![Tests](https://github.com/markotdylan-svg/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/markotdylan-svg/job-watcher/actions/workflows/tests.yml)
[![Daily run](https://github.com/markotdylan-svg/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/markotdylan-svg/job-watcher/actions/workflows/daily.yml)

**Live site:** https://markotdylan-svg.github.io/job-watcher/

Every day, on its own, this tool pulls the open positions at 26 employers from
the job board API of the applicant tracking system (ATS) that hosts each one,
compares them with what it saw before, records what is new and what is gone,
opens a GitHub Issue for the day, and publishes the result to the site above.
The role it watches for is **credit analyst** (any kind: credit risk, credit
underwriting, loan review, and similar).

## How a daily run works

GitHub Actions runs `uv run python -m jobwatcher.run` every day at 13:17 UTC
(`.github/workflows/daily.yml`). Each run:

1. Calls every source and saves what it returns, gzip-compressed, to
   `data/raw/<date>/<source>.json.gz`. A source that fails writes no raw file
   that day; it does not stop the run. Every source's result (ok or failed,
   posting count, error) is logged in `data/runs/<date>.json` and in the status file.
2. Rebuilds `data/history.csv` from the raw files alone (see below).
3. Writes `data/status.json`.
4. Opens a GitHub Issue titled with the date (for example `2026-11-25`) listing
   every new and removed posting with a link, and closes the previous day's issue.
   It is opened every day, even with no changes.
5. Commits the raw files, the history file, the run log and the status file.

The `Deploy site` workflow then publishes `site/` plus the two data files to
GitHub Pages. Dates are UTC (`YYYY-MM-DD`), taken from the moment the run starts.
A second run on the same date deletes and replaces that date's raw files,
rebuilds the history, and edits that date's issue, so each day counts once.

## Building the history file

```bash
uv run python -m jobwatcher.build
```

This reads every `data/raw/<date>/*.json.gz` in date order and writes
`data/history.csv`. It depends on the raw files only, so running it again
produces the same file byte for byte, and a rule change (for example to the
title rule) applies to every day of the history. For each day and each source
that has a raw file that day:

- a posting seen for the first time gets that day as `first_seen`; it is
  `first_run = true` if this is the first raw file of its source;
- every posting the source lists gets that day as `last_seen`;
- an open posting the source no longer lists is marked `removed`, with that day as `removed_date`;
- a removed posting that is listed again becomes `open`, its `removed_date` is
  cleared, and its `first_seen` is kept.

A source with no raw file on a day (a failed fetch) changes nothing that day.
Rows are sorted by `posting_id`, which is `<source>:<the ATS's own id>`.

## Title rule (in_role)

The title is lower-cased and hyphens are treated as spaces. A posting is
**in the role** when the title does **not** contain any of
`engineer, engineering, developer, software, architect, designer, recruiter, sales, fraud, counsel, marketing`
and it matches at least one of:

1. the word **credit** together with an analyst-level word: `analyst`,
   `analysts`, `analytics`, `analysis`, `underwriter`, `underwriting`, or
   `associate` (but not "associate director", "associate general counsel",
   "associate vice president");
2. the word **underwriter(s)**, or the phrase "underwriting analyst" or "underwriting associate";
3. the phrase **loan analyst**, **loan review**, or **lending analyst**.

Examples in the role: *Credit Analyst*, *Sr. Credit Risk Analyst*, *Credit
Underwriter II*, *Home Equity Underwriter*, *Loan Review Analyst*. Not in the role:
*Credit Risk Manager*, *Credit Card Product Manager*, *Credit Risk Software
Engineer*, *Fraud Analyst, Secured Lending*. The rule is in `jobwatcher/rules.py`
and tested in `tests/test_rules.py`. Every posting is kept in the history, in the role or not.

## Sources

Every source returns JSON to a request made with no login; no HTML page is read.

| Source | Employer | ATS | Endpoint |
|---|---|---|---|
| affirm | Affirm | Greenhouse | `boards-api.greenhouse.io/v1/boards/affirm/jobs` |
| block | Block | Greenhouse | `boards-api.greenhouse.io/v1/boards/block/jobs` |
| brex | Brex | Greenhouse | `boards-api.greenhouse.io/v1/boards/brex/jobs` |
| chime | Chime | Greenhouse | `boards-api.greenhouse.io/v1/boards/chime/jobs` |
| coinbase | Coinbase | Greenhouse | `boards-api.greenhouse.io/v1/boards/coinbase/jobs` |
| enova | Enova | Greenhouse | `boards-api.greenhouse.io/v1/boards/enova/jobs` |
| figure | Figure | Greenhouse | `boards-api.greenhouse.io/v1/boards/figure/jobs` |
| mercury | Mercury | Greenhouse | `boards-api.greenhouse.io/v1/boards/mercury/jobs` |
| oportun | Oportun | Greenhouse | `boards-api.greenhouse.io/v1/boards/oportun/jobs` |
| robinhood | Robinhood | Greenhouse | `boards-api.greenhouse.io/v1/boards/robinhood/jobs` |
| sezzle | Sezzle | Greenhouse | `boards-api.greenhouse.io/v1/boards/sezzle/jobs` |
| sofi | SoFi | Greenhouse | `boards-api.greenhouse.io/v1/boards/sofi/jobs` |
| stripe | Stripe | Greenhouse | `boards-api.greenhouse.io/v1/boards/stripe/jobs` |
| upstart | Upstart | Greenhouse | `boards-api.greenhouse.io/v1/boards/upstart/jobs` |
| ramp | Ramp | Ashby | `api.ashbyhq.com/posting-api/job-board/ramp` |
| plaid | Plaid | Ashby | `api.ashbyhq.com/posting-api/job-board/plaid` |
| wealthfront | Wealthfront | Lever | `api.lever.co/v0/postings/wealthfront?mode=json` |
| experian | Experian | SmartRecruiters | `api.smartrecruiters.com/v1/companies/Experian/postings` (paged, 100 per page) |
| capitalone | Capital One | Workday | `capitalone.wd12.myworkdayjobs.com/wday/cxs/capitalone/Capital_One/jobs` |
| keybank | KeyBank | Workday | `keybank.wd5.myworkdayjobs.com/wday/cxs/keybank/External_Career_Site/jobs` |
| mtb | M&T Bank | Workday | `mtb.wd5.myworkdayjobs.com/wday/cxs/mtb/MTB/jobs` |
| pnc | PNC | Workday | `pnc.wd5.myworkdayjobs.com/wday/cxs/pnc/External/jobs` |
| spglobal | S&P Global | Workday | `spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers/jobs` |
| synchrony | Synchrony | Workday | `synchronyfinancial.wd5.myworkdayjobs.com/wday/cxs/synchronyfinancial/Careers/jobs` |
| truist | Truist | Workday | `truist.wd1.myworkdayjobs.com/wday/cxs/truist/Careers/jobs` |
| wellsfargo | Wells Fargo | Workday | `wf.wd1.myworkdayjobs.com/wday/cxs/wf/WellsFargoJobs/jobs` |

**Search terms:** no board returns more than 5,000 postings (the largest, Capital
One, returns about 2,050), so every board is requested in full with **no search
term** (Workday `searchText` is empty). If a board ever grows past 5,000, set
`search_text` for it in `jobwatcher/sources.py` and note the term here.

**Workday notes:** Workday returns 20 postings per request, so a board is paged
until the reported total is reached. Workday rate-limits hard (HTTP 429), so the
Workday boards are fetched one after another with a pause between pages, retried
with backoff, while the other sources are fetched in parallel. A board that is
not finished within 15 minutes counts as failed for that day (no raw file), so it
never causes false removals. The list API gives no department and only a relative
posting date ("Posted 3 Days Ago"), so `department` and `posted_date` are empty
for Workday rows. Greenhouse also leaves `department` empty (it is only returned
with the full job descriptions, which we do not download).

## Data files

`data/history.csv`: one row per posting, with columns `posting_id, source,
source_id, employer, title, location, department, posted_date, url, in_role,
first_run, first_seen, last_seen, status, removed_date`.

`data/status.json` describes the latest run: `run_time` (UTC), `first_run_date`
(date of the earliest raw file), `days_with_success` (number of dates with a raw
file), `open`, `new_today` (first seen in the latest run, first-run postings left
out), `removed_today`, and `sources` (one entry per source with `name`, `ok`,
`count`, plus `employer`, `ats` and `error`). It also has `run_date`.

## Site

Three pages share one navigation bar, `style.css` and `common.js`. Each loads
the data files in the browser and computes everything there.

- **Today** (`index.html`): time of the last run, the status of every source,
  the four counts, and the new and removed postings of the latest run.
- **Browse** (`browse.html`): open postings, credit roles by default with a switch
  to all postings; filters for employer, location and days open; title search;
  sort by first-seen date; an apply link; and a star that saves a posting to a
  shortlist kept in the browser's `localStorage`.
- **Market** (`market.html`): six sections, each computed from `history.csv`:
  new postings per day (all and credit roles; first-run left out), removed
  postings per day, open postings per employer, the median days open (removed,
  non-first-run postings), the share removed within seven days (non-first-run
  postings first seen at least seven days before the last run), and the top
  locations among open postings. "The last run" is the latest `last_seen` date in the history.

The site is installable: `manifest.webmanifest` plus the service worker `sw.js`,
which fetches from the network first (so online visitors always get fresh data),
keeps a copy of every page and data file it loads, and serves that copy when offline.

## Files

| Path | What it does |
|---|---|
| `jobwatcher/sources.py` | The watch list: each employer, its ATS and board id, and its search term if any. |
| `jobwatcher/fetch.py` | Calls each ATS API (with paging, retries and backoff) and reads/writes the gzip raw files. |
| `jobwatcher/normalize.py` | Converts each ATS's raw JSON into the common columns. |
| `jobwatcher/rules.py` | The credit analyst title rule (`in_role`). |
| `jobwatcher/build.py` | Builds `data/history.csv` from the raw files (`python -m jobwatcher.build`). |
| `jobwatcher/status.py` | Computes and writes `data/status.json`. |
| `jobwatcher/issue.py` | Opens or updates the daily GitHub Issue and closes the previous one. |
| `jobwatcher/run.py` | The daily pipeline: fetch, save raw, build, status, issue (`python -m jobwatcher.run`). |
| `tests/test_normalize.py` | Conversion of each ATS (Greenhouse, Lever, Ashby, SmartRecruiters, Workday) to the common columns. |
| `tests/test_rules.py` | The title rule. |
| `tests/test_build.py` | first_seen, last_seen, removed, reopened, failed-source days, first_run, sorting, reproducible build. |
| `tests/test_status_issue.py` | status.json counts and the issue body. |
| `.github/workflows/daily.yml` | Runs the pipeline daily and commits the data. |
| `.github/workflows/tests.yml` | Runs pytest on every push. |
| `.github/workflows/pages.yml` | Publishes the site and data files to GitHub Pages. |
| `site/index.html` | Today page. |
| `site/browse.html` | Browse page. |
| `site/market.html` | Market page. |
| `site/common.js` | Shared code: data loading, CSV parsing, dates, SVG charts with tooltips. |
| `site/style.css` | Shared fonts, colors and layout (light and dark). |
| `site/sw.js` | Service worker for offline use. |
| `site/manifest.webmanifest` | Web app manifest that makes the site installable. |
| `site/icons/` | App icons (192, 512, maskable 512). |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day, compressed. |
| `data/runs/<date>.json` | Every source's result in that day's run (ok, count, error, seconds). |
| `data/history.csv` | One row per posting ever seen. |
| `data/status.json` | Summary of the latest run. |
| `pyproject.toml`, `uv.lock`, `.python-version` | Python project (standard library only; pytest for tests). |
| `.gitattributes` | Forces LF line endings so the history file is identical on every OS. |

## Run it locally

```bash
uv sync
uv run pytest                                  # tests
uv run python -m jobwatcher.build              # rebuild data/history.csv from data/raw
uv run python -m jobwatcher.run --no-issue     # a full run without opening an issue
```
