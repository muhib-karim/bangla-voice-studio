"""Validated mono PCM16 WAV files and bounded streaming assembly."""
from __future__ import annotations
import hashlib
import os
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
        with wave.open(str(path), 'rb') as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise BVSError('INVALID_MEDIA', 'Expected mono PCM16 WAV')
            frames, rate = wav.getnframes(), wav.getframerate()
            remaining = frames * 2
            while remaining:
                chunk = wav.readframes(min(65536, (remaining + 1)//2))
                if not chunk:
                    raise BVSError('INVALID_MEDIA', 'WAV is truncated')
                remaining -= len(chunk)
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(131072), b''):
                digest.update(chunk)
        return AudioArtifact(path, rate, 1, frames, digest.hexdigest())
    except (OSError, EOFError, wave.Error) as exc:
        raise BVSError('INVALID_MEDIA', 'Invalid WAV file') from exc


def read_wav(path: Path) -> tuple[npt.NDArray[np.float32], int]:
    info = inspect_wav(path)
    with wave.open(str(path), 'rb') as wav:
        samples = np.frombuffer(wav.readframes(info.frames), dtype='<i2').astype(np.float32)
    return samples / np.float32(32768), info.sample_rate_hz


def _temporary(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name, suffix='.part', dir=path.parent)
    os.close(fd)
    return Path(name)


def write_wav(path: Path, samples: npt.ArrayLike, sample_rate_hz: int) -> AudioArtifact:
    data = np.asarray(samples)
    if data.ndim != 1 or not np.isfinite(data).all() or sample_rate_hz <= 0:
        raise BVSError('INVALID_MEDIA', 'Expected finite mono audio and positive sample rate')
    pcm = data.astype('<i2') if data.dtype == np.int16 else np.clip(np.rint(data * 32768), -32768, 32767).astype('<i2')
    temporary = _temporary(path)
    try:
        with wave.open(str(temporary), 'wb') as wav:
            wav.setparams((1, 2, sample_rate_hz, 0, 'NONE', 'not compressed'))
            wav.writeframes(pcm.tobytes())
        inspect_wav(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return inspect_wav(path)


def concatenate_wav(paths: Sequence[Path], output_path: Path, *, pause_frames: int = 0) -> AudioArtifact:
    if not paths or pause_frames < 0:
        raise BVSError('INVALID_MEDIA', 'Audio inputs and non-negative pause required')
    infos = [inspect_wav(p) for p in paths]
    rate = infos[0].sample_rate_hz
    if any(i.sample_rate_hz != rate for i in infos):
        raise BVSError('INVALID_MEDIA', 'WAV sample rates must match')
    temporary = _temporary(output_path)
    try:
        with wave.open(str(temporary), 'wb') as target:
            target.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            for index, path in enumerate(paths):
                if index:
                    remaining = pause_frames
                    while remaining:
                        count = min(65536, remaining)
                        target.writeframesraw(b'\0\0' * count)
                        remaining -= count
                with wave.open(str(path), 'rb') as source:
                    while chunk := source.readframes(65536):
                        target.writeframesraw(chunk)
        inspect_wav(temporary)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return inspect_wav(output_path)
