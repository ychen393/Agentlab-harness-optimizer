"""Deterministic tools exposed by the minimal Commerce Agent."""

from datetime import date

from .domain_models import EligibilityRequest, EligibilityResult, Product, PromotionPolicy
from .policies import POLICIES, PRODUCTS, get_policy


DEFAULT_TOOL_DESCRIPTIONS = {
    "search_products": (
        "Find local catalogue products by product name. Use for product lookup, "
        "price, availability, or stock questions."
    ),
    "search_policy": (
        "Look up promotion policy details by policy ID or active date. Use for "
        "questions about promotion dates, minimum spend, or gifts."
    ),
    "check_eligibility": (
        "Check gift eligibility when policy ID, purchase amount, and purchase date "
        "are available."
    ),
}


def search_products(query: str) -> list[Product]:
    normalized_query = query.strip().casefold()
    if not normalized_query:
        raise ValueError("product query is required")
    return [product for product in PRODUCTS if normalized_query in product.name.casefold()]


def search_policy(
    policy_id: str | None = None, active_on: date | None = None
) -> list[PromotionPolicy]:
    if policy_id:
        return [get_policy(policy_id)]
    if active_on:
        return [
            policy
            for policy in POLICIES
            if policy.starts_at <= active_on <= policy.ends_at
        ]
    raise ValueError("policy_id or active_on is required")


def check_eligibility(request: EligibilityRequest) -> EligibilityResult:
    policy = get_policy(request.policy_id)
    if not policy.starts_at <= request.purchase_date <= policy.ends_at:
        return EligibilityResult(
            policy_id=policy.id,
            eligible=False,
            gift=None,
            reason="outside_policy_window",
        )
    if request.purchase_amount < policy.min_amount:
        return EligibilityResult(
            policy_id=policy.id,
            eligible=False,
            gift=None,
            reason="insufficient_purchase_amount",
        )
    return EligibilityResult(
        policy_id=policy.id,
        eligible=True,
        gift=policy.gift,
        reason="eligible",
    )
