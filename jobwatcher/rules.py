"""The title rule that decides whether a posting is in my role: credit analyst.

The title is lower-cased and hyphens are treated as spaces. A posting is in the
role when the title does NOT contain any of

    engineer, engineering, developer, software, architect, designer,
    recruiter, sales, fraud, counsel, marketing

and it matches at least one of:

1. the word "credit" together with an analyst-level word: analyst, analysts,
   analytics, analysis, underwriter, underwriting, or associate (but not
   "associate director", "associate general counsel", "associate vice president");
2. the word "underwriter" (or "underwriters"), or the phrases
   "underwriting analyst" / "underwriting associate";
3. the phrases "loan analyst", "loan review", or "lending analyst".

In the role:   "Credit Analyst", "Sr. Credit Risk Analyst", "Credit Underwriter II",
               "Home Equity Underwriter", "Credit Risk Operations Associate",
               "Loan Review Analyst".
Not in role:   "Credit Risk Manager", "Credit Card Product Manager",
               "Credit Risk Software Engineer", "Fraud Analyst, Secured Lending",
               "Underwriting Manager".
"""

import re

EXCLUDE = re.compile(
    r"\b(engineer|engineering|developer|software|architect|designer|recruiter|sales|fraud|counsel|marketing)\b"
)
CREDIT = re.compile(r"\bcredit\b")
CREDIT_WITH = re.compile(
    r"\b(analyst|analysts|analytics|analysis|underwriter|underwriters|underwriting"
    r"|associate(?! (director|general|vice)))\b"
)
UNDERWRITER = re.compile(r"\b(underwriter|underwriters|underwriting analyst|underwriting associate)\b")
LOAN = re.compile(r"\b(loan analyst|loan review|lending analyst)\b")


def normalize_title(title: str) -> str:
    return " ".join((title or "").lower().replace("-", " ").split())


def in_role(title: str) -> bool:
    t = normalize_title(title)
    if EXCLUDE.search(t):
        return False
    if CREDIT.search(t) and CREDIT_WITH.search(t):
        return True
    return bool(UNDERWRITER.search(t) or LOAN.search(t))
