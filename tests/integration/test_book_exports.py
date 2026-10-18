from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from bvs import media
from bvs.config import Settings
from bvs.errors import BVSError
from bvs.media import encode_audio, ffmetadata, write_wav
from bvs.web.app import create_app

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")

RATE = 24_000
TITLES = ["অধ্যায় ১: শুরু = আরম্ভ; #প্রথম", "শেষ \\ বিদায়"]
BOOK = "# সূচনা\n\nকথা।\n\n# শেষ\n\nবিদায়।"


def _tone(path: Path, seconds: float = 3.0) -> Path:
    t = np.arange(int(RATE * seconds), dtype=np.float32) / RATE
    write_wav(path, 0.2 * np.sin(2 * np.pi * 440 * t), RATE)
    return path


def _probe(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    result: dict[str, Any] = json.loads(out)
    return result


def test_ffmetadata_escapes_special_characters() -> None:
    text = ffmetadata([("a=b;c#d\\e\nf", 0, 1000)], title="বই=১", author="লেখক;")
    assert "title=a\\=b\\;c\\#d\\\\e\\\nf" in text
    assert "title=বই\\=১" in text
    assert "artist=লেখক\\;" in text
    assert text.startswith(";FFMETADATA1\n")
    assert "TIMEBASE=1/1000\nSTART=0\nEND=1000" in text


def test_overlapping_chapters_are_refused() -> None:
    with pytest.raises(BVSError) as err:
        ffmetadata([("one", 0, 2000), ("two", 1500, 3000)])
    assert err.value.code == "EXPORT_FAILED"


@needs_ffmpeg
def test_m4b_carries_chapters_and_metadata(tmp_path: Path) -> None:
    source = _tone(tmp_path / "book.wav")
    out = tmp_path / "book.m4b"
    marks = [(TITLES[0], 0, 1500), (TITLES[1], 1500, 3000)]
    encode_audio(source, out, "m4b", chapters=marks, title="আমার বই", author="লেখক")
    info = _probe(out)
    stream = info["streams"][0]
    assert stream["codec_name"] == "aac"
    assert stream["channels"] == 1
    assert int(stream["sample_rate"]) == RATE
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.1
    assert info["format"]["tags"]["title"] == "আমার বই"
    chapters = info["chapters"]
    assert [c["tags"]["title"] for c in chapters] == TITLES
    for chapter, (_, start_ms, end_ms) in zip(chapters, marks, strict=True):
        assert abs(float(chapter["start_time"]) * 1000 - start_ms) <= 1
        assert abs(float(chapter["end_time"]) * 1000 - end_ms) <= 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["book.m4b", "book.wav"]


@needs_ffmpeg
def test_mp3_is_mono_at_source_rate(tmp_path: Path) -> None:
    out = tmp_path / "speech.mp3"
    encode_audio(_tone(tmp_path / "speech.wav"), out, "mp3", title="শিরোনাম")
    info = _probe(out)
    stream = info["streams"][0]
    assert stream["codec_name"] == "mp3"
    assert stream["channels"] == 1
    assert int(stream["sample_rate"]) == RATE
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.1


@needs_ffmpeg
def test_failed_export_leaves_no_partial_file(tmp_path: Path) -> None:
    source = _tone(tmp_path / "speech.wav")
    out = tmp_path / "missing" / "speech.mp3"
    with pytest.raises(BVSError) as err:
        encode_audio(source, out, "mp3")
    assert err.value.code == "EXPORT_FAILED"
    assert not out.exists()
    assert not out.with_name(out.name + ".part").exists()


def test_missing_ffmpeg_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media.shutil, "which", lambda _name: None)
    with pytest.raises(BVSError) as err:
        encode_audio(tmp_path / "x.wav", tmp_path / "x.mp3", "mp3")
    assert err.value.code == "EXTRA_MISSING"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(
        create_app(Settings(data_dir=tmp_path, model_cache_dir=tmp_path / "models", demo=True))
    ) as client:
        yield client


def _finish(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(400):
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["state"] in {"succeeded", "failed", "cancelled", "interrupted"}:
            assert job["state"] == "succeeded", job
            return dict(job)
        time.sleep(0.05)
    pytest.fail("worker did not finish")


@needs_ffmpeg
def test_audiobook_api_exports_mp3_chapters_and_m4b(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/audiobooks",
        json={
            "engine_id": "dummy",
            "text": BOOK,
            "title": "বই",
            "formats": ["wav", "mp3", "m4b"],
            "captions": ["srt"],
        },
    )
    assert response.status_code == 202, response.text
    job = _finish(client, response.json()["id"])
    result = job["result"]
    kinds = {a["media_type"] for a in result["artifacts"]}
    assert {"audio/wav", "audio/mp4", "application/x-subrip"} <= kinds
    for chapter in result["chapters"]:
        assert {a["media_type"] for a in chapter["artifacts"]} >= {"audio/wav", "audio/mpeg"}
    m4b = next(a for a in result["artifacts"] if a["media_type"] == "audio/mp4")
    download = client.get(m4b["download_url"])
    assert download.status_code == 200
    book = tmp_path / "download.m4b"
    book.write_bytes(download.content)
    info = _probe(book)
    assert [c["tags"]["title"] for c in info["chapters"]] == ["সূচনা", "শেষ"]
    for probed, chapter in zip(info["chapters"], result["chapters"], strict=True):
        assert abs(float(probed["start_time"]) * 1000 - chapter["start_ms"]) <= 1
    ends = [float(c["end_time"]) * 1000 for c in info["chapters"]]
    starts = [c["start_ms"] for c in result["chapters"]]
    for end, next_start in zip(ends, starts[1:], strict=False):
        assert abs(end - next_start) <= 1  # contiguous: the pause stays with its chapter
    assert ends[-1] >= result["chapters"][-1]["end_ms"] - 1
    assert not any("deferred" in w for w in job["result"].get("warnings", []))
