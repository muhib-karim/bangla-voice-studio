from __future__ import annotations

import wave
from pathlib import Path

import pytest

from bvs.chunk_cache import ChunkCache, chunk_key
from bvs.errors import BVSError


def _wav(path: Path, frames: int = 2400) -> Path:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x01\x00" * frames)
    return path


BASE = dict(
    engine_id="dummy",
    model_id="m",
    model_revision="r1",
    text="আমার সোনার বাংলা।",
    language="bn",
    reference=None,
    reference_transcript=None,
    voice_description=None,
    seed=7,
)


def test_key_is_stable_and_every_field_invalidates() -> None:
    key = chunk_key(**BASE)
    assert key == chunk_key(**dict(reversed(list(BASE.items()))))
    assert len(key) == 64
    for field, value in [
        ("model_revision", "r2"),
        ("text", "আমার সোনার বাংলা"),
        ("seed", 8),
        ("voice_description", "calm"),
        ("reference", "ab" * 32),
    ]:
        assert chunk_key(**{**BASE, field: value}) != key, field


def test_store_then_fetch_round_trips_and_counts_hits(tmp_path: Path) -> None:
    cache = ChunkCache(tmp_path / "cache")
    key = chunk_key(**BASE)
    source = _wav(tmp_path / "unit.wav")
    assert not cache.fetch(key, tmp_path / "out.wav")
    cache.store(key, source)
    assert cache.fetch(key, tmp_path / "out.wav")
    assert (tmp_path / "out.wav").read_bytes() == source.read_bytes()
    assert cache.hits == 1
    assert not list((tmp_path / "cache").rglob("*.part"))


def test_corrupt_or_truncated_entry_is_dropped(tmp_path: Path) -> None:
    cache = ChunkCache(tmp_path / "cache")
    key = chunk_key(**BASE)
    cache.store(key, _wav(tmp_path / "unit.wav"))
    stored = next((tmp_path / "cache").rglob("*.wav"))
    stored.write_bytes(stored.read_bytes()[:20])
    assert not cache.fetch(key, tmp_path / "out.wav")
    assert not stored.exists() and not stored.with_suffix(".json").exists()
    assert cache.hits == 0


def test_malformed_key_cannot_escape_the_cache(tmp_path: Path) -> None:
    cache = ChunkCache(tmp_path / "cache")
    with pytest.raises(BVSError):
        cache.store("../" + "a" * 61, _wav(tmp_path / "unit.wav"))
