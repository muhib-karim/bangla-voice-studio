"""Smoke scoring is deterministic; model execution stays in Actions."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def smoke_module() -> ModuleType:
    path = Path(__file__).parents[2] / "scripts/model_smoke.py"
    spec = importlib.util.spec_from_file_location("model_smoke", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("reference", "heard", "expected"),
    [
        ("বাংলা।", "বাংলা!", 0.0),
        ("abc", "adc", 1 / 3),
        ("abc", "ab", 1 / 3),
        ("abc", "abcd", 1 / 3),
        ("a", "", 1.0),
    ],
)
def test_cer_counts_substitutions_deletions_insertions(
    reference: str, heard: str, expected: float
) -> None:
    assert smoke_module().cer(reference, heard) == pytest.approx(expected)


def test_empty_reference_is_not_a_score() -> None:
    with pytest.raises(ValueError):
        smoke_module().cer(" । ", "কথা")


def test_real_execution_requires_explicit_actions_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(SystemExit, match="GitHub Actions"):
        smoke_module().require_actions()
