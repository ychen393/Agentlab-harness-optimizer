"""Small deterministic scenario set for the Commerce Agent testbed."""

from .domain_models import CommerceGroundTruth, CommerceScenario
from app.schemas import TestCase


COMMERCE_SCENARIOS: tuple[CommerceScenario, ...] = (
    CommerceScenario(
        id="CS1",
        test_case=TestCase(
            id="CT1",
            input="Check gift eligibility for POLICY_A on 2026-01-15 with purchase amount 550.",
            category="normal",
            difficulty="easy",
            requirement_ids=["R_ELIGIBILITY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_policy_id="POLICY_A",
            expected_eligible=True,
            expected_gift="Gift A",
        ),
    ),
    CommerceScenario(
        id="CS2",
        test_case=TestCase(
            id="CT2",
            input="Check gift eligibility for POLICY_B on 2026-02-10 with purchase amount 650.",
            category="normal",
            difficulty="easy",
            requirement_ids=["R_ELIGIBILITY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_policy_id="POLICY_B",
            expected_eligible=True,
            expected_gift="Gift B",
        ),
    ),
    CommerceScenario(
        id="CS3",
        test_case=TestCase(
            id="CT3",
            input="Check gift eligibility for POLICY_B on 2026-02-10 with purchase amount 550.",
            category="boundary",
            difficulty="medium",
            requirement_ids=["R_ELIGIBILITY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_policy_id="POLICY_B",
            expected_eligible=False,
        ),
    ),
    CommerceScenario(
        id="CS4",
        test_case=TestCase(
            id="CT4",
            input="Check gift eligibility for POLICY_A on 2026-01-31 with purchase amount 500.",
            category="boundary",
            difficulty="medium",
            requirement_ids=["R_ELIGIBILITY", "R_BOUNDARY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_policy_id="POLICY_A",
            expected_eligible=True,
            expected_gift="Gift A",
        ),
    ),
    CommerceScenario(
        id="CS5",
        test_case=TestCase(
            id="CT5",
            input="Am I eligible for a promotion gift?",
            category="missing_context",
            difficulty="hard",
            requirement_ids=["R_ELIGIBILITY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_error=True,
        ),
    ),
    CommerceScenario(
        id="CS6",
        test_case=TestCase(
            id="CT6",
            input=(
                "My order was paid on 2026-02-10 for 650 RMB. "
                "Which promotion applies, and do I qualify for the gift?"
            ),
            category="tool_required",
            difficulty="medium",
            requirement_ids=["R_ELIGIBILITY", "R_POLICY_DISCOVERY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_tool_calls=("search_policy", "check_eligibility"),
            expected_policy_id="POLICY_B",
            expected_eligible=True,
            expected_gift="Gift B",
        ),
    ),
    CommerceScenario(
        id="CS7",
        test_case=TestCase(
            id="CT7",
            input=(
                "My order was paid on 2026-02-10 for 550 RMB. "
                "Which promotion applies, and do I qualify for the gift?"
            ),
            category="tool_required",
            difficulty="medium",
            requirement_ids=["R_ELIGIBILITY", "R_POLICY_DISCOVERY"],
        ),
        ground_truth=CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_tool_calls=("search_policy", "check_eligibility"),
            expected_policy_id="POLICY_B",
            expected_eligible=False,
            expected_gift=None,
        ),
    ),
)
