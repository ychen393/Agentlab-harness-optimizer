from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_frontend_patch_flow_uses_real_patch_endpoint_and_artifact() -> None:
    source = (ROOT / "frontend" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "generatePatch" in source
    assert "patchResult?.patch" in source
    assert "snapshot.patch" not in source


def test_frontend_does_not_apply_patch_or_enter_validated_state() -> None:
    source = (ROOT / "frontend" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert 'onApply={() => setState("validated")}' not in source
    assert 'setState("validated")' not in source
    assert 'disabled title={t(language, "applyDisabled")}' in source


def test_patch_unavailable_stays_on_diagnosis_surface() -> None:
    source = (ROOT / "frontend" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert 'result.status === "patch_ready" && result.patch' in source
    assert 'setRunError(result.message ?? t(language, "patchUnavailable"))' in source
