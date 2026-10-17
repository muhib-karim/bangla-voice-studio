"""M3.1: exported captions are parsed independently and checked against the audio clock."""

import re
import wave
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bvs.cli import app

runner = CliRunner()

TEXT = "আজ আকাশ পরিষ্কার। তুমি কি আসবে? খুব ভালো!"
SRT_TIME = re.compile(r"^(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})$")
VTT_TIME = re.compile(r"^(\d\d):(\d\d):(\d\d)\.(\d{3}) --> (\d\d):(\d\d):(\d\d)\.(\d{3})")


def _ms(h: str, m: str, s: str, ms: str) -> int:
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def _cues(text: str, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    cues = []
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            g = match.groups()
            cues.append((_ms(*g[:4]), _ms(*g[4:])))
    return cues


def _wav_ms(path: Path) -> float:
    with wave.open(str(path)) as handle:
        return handle.getnframes() * 1000 / handle.getframerate()


def _assert_timeline(cues: list[tuple[int, int]], audio_ms: float) -> None:
    assert cues, "no cues parsed"
    previous_end = 0
    for start, end in cues:
        assert previous_end <= start <= end
        previous_end = end
    # Cue clocks come from real frame counts, so the last cue ends inside the audio.
    assert cues[-1][1] <= audio_ms + 1


def test_say_exports_srt_and_vtt_on_the_audio_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BVS_DATA_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BVS_MODEL_CACHE", str(tmp_path / "models"))
    out = tmp_path / "speech.wav"
    result = runner.invoke(
        app, ["say", TEXT, "--engine", "dummy", "--output", str(out), "--srt", "--vtt"]
    )
    assert result.exit_code == 0, result.output
    audio_ms = _wav_ms(out)
    assert audio_ms > 0

    srt = out.with_suffix(".srt").read_text(encoding="utf-8")
    srt_cues = _cues(srt, SRT_TIME)
    _assert_timeline(srt_cues, audio_ms)
    assert srt.lstrip().startswith("1\n")

    vtt = out.with_suffix(".vtt").read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT")
    vtt_cues = _cues(vtt, VTT_TIME)
    _assert_timeline(vtt_cues, audio_ms)

    # Both formats describe the same timeline.
    assert srt_cues == vtt_cues
