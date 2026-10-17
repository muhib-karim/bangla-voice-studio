"""Stable, dependency-free engine contracts."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

CommercialUse = Literal["allowed", "non-commercial", "unknown"]
EngineKind = Literal["tts", "asr"]
Device = Literal["cpu", "cuda"]

@dataclass(frozen=True)
class LicenseInfo:
    identifier: str                  # SPDX or LicenseRef; unknown is explicit
    url: str | None
    commercial_use: CommercialUse
    notes: str

@dataclass(frozen=True)
class Capabilities:
    languages: tuple[str, ...]       # application uses ISO 639-1, e.g. bn/en
    cloning: bool
    reference_required: bool
    voice_description: bool
    word_timestamps: bool
    segment_timestamps: bool
    sample_rate_hz: int | None       # native TTS output; None until verified/ASR
    max_text_chars: int | None       # conservative adapter limit, not token limit
    max_reference_seconds: float | None

@dataclass(frozen=True)
class EngineSpec:
    id: str
    kind: EngineKind
    display_name: str
    model_id: str | None
    model_revision: str | None       # release pins a commit, never mutable main
    factory: str                    # "bvs.engines.mms:create_engine"
    pip_extra: str | None
    capabilities: Capabilities
    license: LicenseInfo
    approximate_download_bytes: int | None
    estimated_ram_bytes: int | None
    estimated_vram_bytes: int | None
    maturity: Literal["test-only", "verified", "experimental", "planned"]

@dataclass(frozen=True)
class RuntimeConfig:
    model_cache_dir: Path
    work_dir: Path
    model_id: str | None
    model_revision: str | None
    device: Device = "cpu"
    cpu_threads: int = 2
    offline: bool = True

@dataclass(frozen=True)
class Progress:
    phase: str
    completed: int
    total: int | None
    unit: Literal["chunks", "segments", "bytes", "steps"]
    message: str

@dataclass(frozen=True)
class RunContext:
    report: Callable[[Progress], None]
    is_cancelled: Callable[[], bool]

@dataclass(frozen=True)
class ReferenceAudio:
    wav_path: Path
    transcript: str
    language: str = "bn"

@dataclass(frozen=True)
class SynthesisRequest:
    text: str                       # exactly one prepared unit; already normalised
    language: str = "bn"
    reference: ReferenceAudio | None = None
    voice_description: str | None = None
    seed: int = 0

@dataclass(frozen=True)
class AudioArtifact:
    path: Path
    sample_rate_hz: int
    channels: Literal[1]
    frames: int
    sha256: str

@dataclass(frozen=True)
class SynthesisResult:
    audio: AudioArtifact
    engine_id: str
    model_revision: str | None
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class ASRRequest:
    audio_path: Path
    language: Literal["bn", "en"] | None = "bn"  # None means auto
    word_timestamps: bool = True

@dataclass(frozen=True)
class Word:
    text: str
    start_seconds: float
    end_seconds: float
    confidence: float | None = None

@dataclass(frozen=True)
class Segment:
    text: str
    start_seconds: float
    end_seconds: float
    words: tuple[Word, ...] = ()

@dataclass(frozen=True)
class ASRResult:
    text: str
    language: str
    duration_seconds: float
    segments: tuple[Segment, ...]
    word_timestamps_available: bool
    engine_id: str
    model_revision: str | None
    warnings: tuple[str, ...] = ()

class Engine(Protocol):
    @property
    def spec(self) -> EngineSpec: ...
    def load(self, config: RuntimeConfig, context: RunContext) -> None: ...
    def synthesize(
        self, request: SynthesisRequest, *, output_path: Path,
        context: RunContext,
    ) -> SynthesisResult: ...
    def unload(self) -> None: ...

class ASREngine(Protocol):
    @property
    def spec(self) -> EngineSpec: ...
    def load(self, config: RuntimeConfig, context: RunContext) -> None: ...
    def transcribe(self, request: ASRRequest, *, context: RunContext) -> ASRResult: ...
    def unload(self) -> None: ...
