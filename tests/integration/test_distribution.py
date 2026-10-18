"""Checks on the built wheel (PLAN M3.4).

The wheel is built once per module from the working tree. These tests need the
``build`` package from the dev extra and network access for the isolated build
backend, so they run on CI and skip elsewhere.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest

import bvs

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("build") is None,
    reason="needs the 'build' package from the dev extra",
)


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    wheels = sorted(out.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def _names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


def _dist_info_file(wheel: Path, name: str) -> str:
    with zipfile.ZipFile(wheel) as archive:
        matches = [n for n in archive.namelist() if n.endswith(f".dist-info/{name}")]
        assert len(matches) == 1, matches
        return archive.read(matches[0]).decode("utf-8")


def test_wheel_carries_the_studio_assets(wheel: Path) -> None:
    names = set(_names(wheel))
    for asset in (
        "bvs/web/static/index.html",
        "bvs/web/static/app.js",
        "bvs/web/static/fonts/NotoSansBengali.ttf",
        "bvs/web/static/fonts/OFL.txt",
    ):
        assert asset in names


def test_wheel_leaves_out_tests_and_project_notes(wheel: Path) -> None:
    for name in _names(wheel):
        assert not name.startswith(("tests/", "scripts/", "site/", "docs/")), name
        assert not name.endswith(("PLAN.md", "REVIEW.md", ".pyc")), name


def test_wheel_metadata_matches_the_package(wheel: Path) -> None:
    metadata = Parser().parsestr(_dist_info_file(wheel, "METADATA"))
    assert metadata["Name"] == "bangla-voice-studio"
    assert metadata["Version"] == bvs.__version__
    assert metadata["Requires-Python"] == ">=3.11"
    heavy = ("torch", "transformers", "faster-whisper", "faster_whisper")
    for requirement in metadata.get_all("Requires-Dist") or []:
        if requirement.lower().startswith(heavy):
            assert "extra ==" in requirement, requirement


def test_wheel_installs_the_bvs_command(wheel: Path) -> None:
    entry_points = _dist_info_file(wheel, "entry_points.txt")
    assert "[console_scripts]" in entry_points
    assert "bvs = bvs.cli:app" in entry_points


def test_wheel_ships_the_licence(wheel: Path) -> None:
    licences = [n for n in _names(wheel) if ".dist-info/" in n and n.endswith("LICENSE")]
    assert licences
