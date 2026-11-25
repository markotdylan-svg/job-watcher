"""The title rule for the credit analyst role."""

import pytest

from jobwatcher.rules import in_role


@pytest.mark.parametrize("title", [
    "Credit Analyst",
    "Senior Credit Analyst",
    "Sr. Credit Risk Analyst",
    "Commercial Credit Analytics Associate",
    "Credit Underwriter II",
    "Credit Risk Operations Associate",
    "CREDIT ANALYST - Middle Market",
    "Home Equity Underwriter",
    "Underwriter",
    "Senior Underwriting Associate",
    "Loan Review Analyst",
    "Lending Analyst, Small Business",
    "Credit Portfolio Analysis Lead",
])
def test_in_role(title):
    assert in_role(title)


@pytest.mark.parametrize("title", [
    "",
    "Credit Risk Manager",
    "Director, Credit Risk",
    "Credit Card Product Manager",
    "Credit Risk Software Engineer",
    "Senior Data Engineer, Credit Reporting",
    "Fraud Analyst, Secured Lending",
    "Underwriting Manager",
    "Associate General Counsel, Banking and Credit Cards",
    "Associate Director, Credit Products",
    "Account Executive - Credit",
    "Financial Analyst",
    "Loan Closer",
    "Discredited Analyst",  # "credit" must be a whole word
])
def test_not_in_role(title):
    assert not in_role(title)


def test_none_title():
    assert not in_role(None)
