import json
import shutil
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bvs.cli import app

runner = CliRunner()


def test_help_normalize_and_engines_without_heavy_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BVS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BVS_MODEL_CACHE", str(tmp_path / "models"))
    assert runner.invoke(app, ["--help"]).exit_code == 0
    result = runner.invoke(app, ["normalize", "৳৫০"])
    assert result.exit_code == 0 and result.stdout.strip() == "পঞ্চাশ টাকা"
    result = runner.invoke(app, ["engines", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert any(row["id"] == "mms" for row in json.loads(result.stdout))
    assert not {"torch", "transformers", "faster_whisper"} & sys.modules.keys()


def test_dummy_say_no_overwrite_and_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BVS_DATA_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BVS_MODEL_CACHE", str(tmp_path / "models"))
    out = tmp_path / "tone.wav"
    args = ["say", "কথা", "--engine", "dummy", "--output", str(out), "--srt"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert out.read_bytes().startswith(b"RIFF")
    assert out.with_suffix(".srt").exists()
    assert runner.invoke(app, args).exit_code == 2
    assert (
        runner.invoke(
            app, ["say", "কথা", "--engine", "mms", "--output", str(tmp_path / "real.wav")]
        ).exit_code
        == 3
    )
    assert runner.invoke(app, ["serve", "--host", "0.0.0.0"]).exit_code == 2


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_dummy_say_writes_mp3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BVS_DATA_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BVS_MODEL_CACHE", str(tmp_path / "models"))
    out = tmp_path / "tone.mp3"
    result = runner.invoke(app, ["say", "কথা", "--engine", "dummy", "--output", str(out)])
    assert result.exit_code == 0, result.output
    head = out.read_bytes()[:3]
    assert head == b"ID3" or head[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
    assert not out.with_suffix(".wav").exists()
    bad = runner.invoke(
        app, ["say", "কথা", "--engine", "dummy", "--output", str(tmp_path / "x.ogg")]
    )
    assert bad.exit_code == 2
