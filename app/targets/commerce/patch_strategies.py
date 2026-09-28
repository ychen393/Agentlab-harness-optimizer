"""Commerce-specific bounded patch proposal strategies.

These strategies implement target knowledge while conforming to the generic
AgentLab Core ``PatchProposalStrategy`` contract.
"""

from app.optimizer import (
    PatchProposalStrategy,
    SystemPromptConstraintPatchStrategy,
    ToolArgumentSchemaPatchStrategy,
)
from app.schemas import AgentConfig, FailurePattern, HarnessPatch, RootCauseAnalysis


class CommerceSystemPromptPatchStrategy(SystemPromptConstraintPatchStrategy):
    """Compatibility alias for the generic constraint-derived strategy."""


class CommerceToolDescriptionPatchStrategy(ToolArgumentSchemaPatchStrategy):
    """Compatibility alias for the generic contract-derived strategy."""


def commerce_patch_strategies() -> tuple[PatchProposalStrategy, ...]:
    """Return Commerce strategies to register alongside Core strategies."""

    return (
        CommerceSystemPromptPatchStrategy(),
        CommerceToolDescriptionPatchStrategy(),
    )
