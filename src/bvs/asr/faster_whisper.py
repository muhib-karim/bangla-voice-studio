"""Faster Whisper small; dependencies are loaded only by load()."""

from bvs.contracts import ASREngine, Capabilities, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "faster-whisper",
    "asr",
    "Faster Whisper small",
    "Systran/faster-whisper-small",
    None,
    "bvs.asr.faster_whisper:create_engine",
    "asr",
    Capabilities(
        ("bn", "en"),
        False,
        False,
        False,
        True,
        True,
        None,
        500,
        None,
    ),
    LicenseInfo(
        "LicenseRef-Unknown",
        None,
        "unknown",
        "Model validation pending",
    ),
    None,
    None,
    None,
    "experimental",
)


def create_engine() -> ASREngine:
    from bvs.registry import _make_engine

    return _make_engine(SPEC)
