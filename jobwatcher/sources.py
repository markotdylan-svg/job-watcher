"""The watch list: every employer the tool reads, and the job board API that hosts it.

Each source is read through the public JSON API of its applicant tracking system
(ATS). None of them needs a login, and none of them is an HTML page.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    name: str  # short id, used in posting_id and in the raw file name
    employer: str  # display name
    ats: str  # greenhouse | lever | ashby | smartrecruiters | workday
    config: dict = field(default_factory=dict)
    search_text: str = ""  # only used for boards that return more than 5,000 postings


def gh(name, employer, board):
    return Source(name, employer, "greenhouse", {"board": board})


def workday(name, employer, host, tenant, site):
    return Source(name, employer, "workday", {"host": host, "tenant": tenant, "site": site})


SOURCES: list[Source] = [
    # Greenhouse
    gh("affirm", "Affirm", "affirm"),
    gh("block", "Block", "block"),
    gh("brex", "Brex", "brex"),
    gh("chime", "Chime", "chime"),
    gh("coinbase", "Coinbase", "coinbase"),
    gh("enova", "Enova", "enova"),
    gh("figure", "Figure", "figure"),
    gh("mercury", "Mercury", "mercury"),
    gh("oportun", "Oportun", "oportun"),
    gh("robinhood", "Robinhood", "robinhood"),
    gh("sezzle", "Sezzle", "sezzle"),
    gh("sofi", "SoFi", "sofi"),
    gh("stripe", "Stripe", "stripe"),
    gh("upstart", "Upstart", "upstart"),
    # Ashby
    Source("ramp", "Ramp", "ashby", {"board": "ramp"}),
    Source("plaid", "Plaid", "ashby", {"board": "plaid"}),
    # Lever
    Source("wealthfront", "Wealthfront", "lever", {"site": "wealthfront"}),
    # SmartRecruiters
    Source("experian", "Experian", "smartrecruiters", {"company": "Experian"}),
    # Workday
    workday("capitalone", "Capital One", "capitalone.wd12.myworkdayjobs.com", "capitalone", "Capital_One"),
    workday("keybank", "KeyBank", "keybank.wd5.myworkdayjobs.com", "keybank", "External_Career_Site"),
    workday("mtb", "M&T Bank", "mtb.wd5.myworkdayjobs.com", "mtb", "MTB"),
    workday("pnc", "PNC", "pnc.wd5.myworkdayjobs.com", "pnc", "External"),
    workday("spglobal", "S&P Global", "spgi.wd5.myworkdayjobs.com", "spgi", "SPGI_Careers"),
    workday("synchrony", "Synchrony", "synchronyfinancial.wd5.myworkdayjobs.com", "synchronyfinancial", "Careers"),
    workday("truist", "Truist", "truist.wd1.myworkdayjobs.com", "truist", "Careers"),
    workday("wellsfargo", "Wells Fargo", "wf.wd1.myworkdayjobs.com", "wf", "WellsFargoJobs"),
]

SOURCES_BY_NAME = {s.name: s for s in SOURCES}
