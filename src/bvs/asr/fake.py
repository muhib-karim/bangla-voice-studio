"""Simulated fixture transcript; dependencies are loaded only by load()."""

from bvs.contracts import ASREngine, Capabilities, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "fake-asr",
    "asr",
    "Simulated fixture transcript",
    None,
    None,
    "bvs.asr.fake:create_engine",
    None,
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
    LicenseInfo("MIT", None, "allowed", ""),
    0,
    None,
    None,
    "test-only",
)


def create_engine() -> ASREngine:
    from bvs.registry import _make_engine

    return _make_engine(SPEC)
