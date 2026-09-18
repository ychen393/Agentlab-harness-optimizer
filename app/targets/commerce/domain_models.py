"""Commerce-specific domain and immutable ground-truth models."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import TestCase


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    price: int = Field(ge=0)
    stock: int = Field(ge=0)


class PromotionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    starts_at: date
    ends_at: date
    min_amount: int = Field(ge=0)
    gift: str


class EligibilityRequest(BaseModel):
    policy_id: str
    purchase_amount: int = Field(ge=0)
    purchase_date: date


class EligibilityResult(BaseModel):
    policy_id: str
    eligible: bool
    gift: str | None
    reason: Literal[
        "eligible",
        "outside_policy_window",
        "insufficient_purchase_amount",
    ]


class CommerceGroundTruth(BaseModel):
    """Immutable expected outcome for a CommerceScenario."""

    model_config = ConfigDict(frozen=True)

    expected_tool: Literal["search_products", "search_policy", "check_eligibility"]
    expected_policy_id: str | None = None
    expected_eligible: bool | None = None
    expected_gift: str | None = None
    expected_error: bool = False


class CommerceScenario(BaseModel):
    """A generic TestCase paired with commerce-owned ground truth."""

    model_config = ConfigDict(frozen=True)

    id: str
    test_case: TestCase
    ground_truth: CommerceGroundTruth
