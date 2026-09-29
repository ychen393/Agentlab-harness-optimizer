from pathlib import Path


WORKFLOW_SOURCE = (
    Path(__file__).parents[1] / "frontend" / "lib" / "workflow.ts"
).read_text(encoding="utf-8")


def test_every_workflow_state_has_an_explicit_stage() -> None:
    expected = {
        "ready: 1",
        "execution: 2",
        "execution_failed: 2",
        "diagnosed: 3",
        "patch_ready: 4",
        "validated: 5",
    }

    assert all(item in WORKFLOW_SOURCE for item in expected)
    assert "return WORKFLOW_STAGE[state]" in WORKFLOW_SOURCE
    assert "default" not in WORKFLOW_SOURCE


def test_execution_states_do_not_map_to_validation_stage() -> None:
    assert "execution: 2" in WORKFLOW_SOURCE
    assert "execution_failed: 2" in WORKFLOW_SOURCE
    assert "validated: 5" in WORKFLOW_SOURCE
