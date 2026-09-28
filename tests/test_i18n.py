"""Guard the bilingual UI contract against missing translation keys."""
from __future__ import annotations

from itertools import chain
from pathlib import Path

from app.ui.i18n import TEXT, collect_ui_translation_keys


def _ui_translation_keys() -> set[str]:
    return collect_ui_translation_keys()


def test_translation_dictionaries_have_identical_keys() -> None:
    zh_keys = set(TEXT["zh"])
    en_keys = set(TEXT["en"])
    assert zh_keys == en_keys, (
        f"Missing from zh: {sorted(en_keys - zh_keys)}; "
        f"missing from en: {sorted(zh_keys - en_keys)}"
    )


def test_streamlit_translation_keys_exist_in_both_languages() -> None:
    referenced = _ui_translation_keys()
    missing_zh = referenced - set(TEXT["zh"])
    missing_en = referenced - set(TEXT["en"])
    assert not missing_zh and not missing_en, (
        f"Missing from zh: {sorted(missing_zh)}; missing from en: {sorted(missing_en)}"
    )


def test_actual_agentlab_entrypoint_is_scanned() -> None:
    assert "regression_intro" in collect_ui_translation_keys(Path(__file__).parents[1])


def test_agentlab_entrypoint_reaches_evidence_chain() -> None:
    from streamlit.testing.v1 import AppTest

    entrypoint = Path(__file__).parents[1] / "agentlab_ui.py"
    app = AppTest.from_file(entrypoint).run(timeout=20)
    app.session_state["demo_step"] = 2
    app.run(timeout=20)
    assert not app.exception
    elements = chain(app.subheader, app.markdown, app.caption)
    assert any("ExecutionTrace" in item.value for item in elements)
