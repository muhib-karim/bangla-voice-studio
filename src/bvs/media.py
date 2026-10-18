"""Validated mono PCM16 WAV files and bounded streaming assembly."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt

from bvs.contracts import AudioArtifact
from bvs.errors import BVSError


def inspect_wav(path: Path) -> AudioArtifact:
    try:
        with wave.open(str(path), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise BVSError("INVALID_MEDIA", "Expected mono PCM16 WAV")
            frames, rate = wav.getnframes(), wav.getframerate()
            remaining = frames * 2
            while remaining:
                chunk = wav.readframes(min(65536, (remaining + 1) // 2))
                if not chunk:
                    raise BVSError("INVALID_MEDIA", "WAV is truncated")
                remaining -= len(chunk)
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(131072), b""):
                digest.update(chunk)
        return AudioArtifact(path, rate, 1, frames, digest.hexdigest())
    except (OSError, EOFError, wave.Error) as exc:
        raise BVSError("INVALID_MEDIA", "Invalid WAV file") from exc


def read_wav(path: Path) -> tuple[npt.NDArray[np.float32], int]:
    info = inspect_wav(path)
    with wave.open(str(path), "rb") as wav:
        samples = np.frombuffer(wav.readframes(info.frames), dtype="<i2").astype(np.float32)
    return samples / np.float32(32768), info.sample_rate_hz


def _temporary(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name, suffix=".part", dir=path.parent)
    os.close(fd)
    return Path(name)


def write_wav(path: Path, samples: npt.ArrayLike, sample_rate_hz: int) -> AudioArtifact:
    data = np.asarray(samples)
    if data.ndim != 1 or not np.isfinite(data).all() or sample_rate_hz <= 0:
        raise BVSError("INVALID_MEDIA", "Expected finite mono audio and positive sample rate")
    pcm = (
        data.astype("<i2")
        if data.dtype == np.int16
        else np.clip(np.rint(data * 32768), -32768, 32767).astype("<i2")
    )
    temporary = _temporary(path)
    try:
        with wave.open(str(temporary), "wb") as wav:
            wav.setparams((1, 2, sample_rate_hz, 0, "NONE", "not compressed"))
            wav.writeframes(pcm.tobytes())
        inspect_wav(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return inspect_wav(path)


def concatenate_wav(
    paths: Sequence[Path], output_path: Path, *, pause_frames: int = 0
) -> AudioArtifact:
    if not paths or pause_frames < 0:
        raise BVSError("INVALID_MEDIA", "Audio inputs and non-negative pause required")
    infos = [inspect_wav(p) for p in paths]
    rate = infos[0].sample_rate_hz
    if any(i.sample_rate_hz != rate for i in infos):
        raise BVSError("INVALID_MEDIA", "WAV sample rates must match")
    temporary = _temporary(output_path)
    try:
        with wave.open(str(temporary), "wb") as target:
            target.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            for index, path in enumerate(paths):
                if index:
                    remaining = pause_frames
                    while remaining:
                        count = min(65536, remaining)
                        target.writeframesraw(b"\0\0" * count)
                        remaining -= count
                with wave.open(str(path), "rb") as source:
                    while chunk := source.readframes(65536):
                        target.writeframesraw(chunk)
        inspect_wav(temporary)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return inspect_wav(output_path)


def _ffmetadata_escape(value: str) -> str:
    """Escape a value for an ffmetadata file (``=``, ``;``, ``#``, ``\\`` and newlines)."""
    out = []
    for char in value:
        if char in "=;#\\\n":
            out.append("\\")
        out.append(char)
    return "".join(out)


def ffmetadata(
    chapters: Sequence[tuple[str, int, int]], *, title: str = "", author: str = ""
) -> str:
    """Render UTF-8 ffmetadata with millisecond chapters given as (title, start_ms, end_ms)."""
    lines = [";FFMETADATA1"]
    if title:
        lines.append("title=" + _ffmetadata_escape(title))
        lines.append("album=" + _ffmetadata_escape(title))
    if author:
        lines.append("artist=" + _ffmetadata_escape(author))
    previous = 0
    for name, start_ms, end_ms in chapters:
        if start_ms < previous or end_ms <= start_ms:
            raise BVSError("EXPORT_FAILED", "Chapter times must be increasing")
        previous = end_ms
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start_ms}",
            f"END={end_ms}",
            "title=" + _ffmetadata_escape(name),
        ]
    return "\n".join(lines) + "\n"


def encode_audio(
    source: Path,
    output_path: Path,
    fmt: str,
    *,
    chapters: Sequence[tuple[str, int, int]] = (),
    title: str = "",
    author: str = "",
    timeout: float = 3600,
) -> Path:
    """Encode a canonical WAV as MP3 (128 kbps mono) or chaptered AAC-in-M4B (64 kbps mono).

    The output is written to a temporary file and moved into place only after ffmpeg
    succeeds, so a failed or cancelled export never leaves a truncated file behind.
    """
    if fmt not in {"mp3", "m4b"}:
        raise BVSError("EXPORT_FAILED", "Unsupported export format")
    executable = shutil.which("ffmpeg")
    if not executable:
        raise BVSError("EXTRA_MISSING", "Install ffmpeg for MP3/M4B export")
    info = inspect_wav(source)
    temporary = output_path.with_name(output_path.name + ".part")
    meta = output_path.with_name(output_path.name + ".ffmeta")
    command = [executable, "-nostdin", "-v", "error", "-y", "-i", str(source)]
    try:
        if fmt == "m4b":
            meta.write_text(ffmetadata(chapters, title=title, author=author), encoding="utf-8")
            command += ["-f", "ffmetadata", "-i", str(meta), "-map", "0:a"]
            command += ["-map_metadata", "1", "-map_chapters", "1"]
            command += ["-c:a", "aac", "-b:a", "64k", "-ac", "1", "-ar", str(info.sample_rate_hz)]
            command += ["-movflags", "+faststart", "-f", "mp4", str(temporary)]
        else:
            command += ["-map", "0:a", "-c:a", "libmp3lame", "-b:a", "128k", "-ac", "1"]
            command += ["-ar", str(info.sample_rate_hz), "-id3v2_version", "3"]
            if title:
                command += ["-metadata", "title=" + title]
            if author:
                command += ["-metadata", "artist=" + author]
            command += ["-f", "mp3", str(temporary)]
        subprocess.run(command, check=True, capture_output=True, timeout=timeout)
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise BVSError("EXPORT_FAILED", "Encoder produced no output")
        os.replace(temporary, output_path)
    except (subprocess.SubprocessError, OSError) as exc:
        raise BVSError("EXPORT_FAILED", f"{fmt.upper()} export failed") from exc
    finally:
        temporary.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
    return output_path
