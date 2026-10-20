"""Minimal deterministic Commerce Target Agent testbed."""

from .agent import CommerceAgent
from .challenges import challenge_family, generate_challenges, run_challenges
from .config import commerce_v1_config
from .coverage import analyze_coverage, exploratory_family
from .evaluator import evaluate_commerce
from .phase13 import (
    analyze_commerce_tool_argument_root_cause,
    assess_deterministic_patchability,
    propose_commerce_tool_description_patch,
    run_harness_sensitive_cycle,
    validate_harness_candidate,
)
from .patch_strategies import (
    CommerceSystemPromptPatchStrategy,
    CommerceToolDescriptionPatchStrategy,
    commerce_patch_strategies,
)
from .scenarios import COMMERCE_SCENARIOS
from .tool_contract_demo import (
    ContractSensitiveRouter,
    TOOL_CONTRACT_CASES,
    TOOL_CONTRACT_CONTROL,
    TOOL_CONTRACT_HELDOUT,
    TOOL_CONTRACT_SEED,
    ToolContractRepairProof,
    build_tool_contract_repair_proof,
    tool_contract_baseline_config,
)

__all__ = [
    "COMMERCE_SCENARIOS",
    "CommerceAgent",
    "CommerceSystemPromptPatchStrategy",
    "CommerceToolDescriptionPatchStrategy",
    "assess_deterministic_patchability",
    "analyze_commerce_tool_argument_root_cause",
    "analyze_coverage",
    "challenge_family",
    "commerce_v1_config",
    "commerce_patch_strategies",
    "evaluate_commerce",
    "exploratory_family",
    "generate_challenges",
    "propose_commerce_tool_description_patch",
    "run_challenges",
    "run_harness_sensitive_cycle",
    "validate_harness_candidate",
    "ContractSensitiveRouter",
    "TOOL_CONTRACT_CASES",
    "TOOL_CONTRACT_CONTROL",
    "TOOL_CONTRACT_HELDOUT",
    "TOOL_CONTRACT_SEED",
    "ToolContractRepairProof",
    "build_tool_contract_repair_proof",
    "tool_contract_baseline_config",
]
