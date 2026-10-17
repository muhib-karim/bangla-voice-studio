"""Demo tone — not speech.; dependencies are loaded only by load()."""

from bvs.contracts import Capabilities, Engine, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "dummy",
    "tts",
    "Demo tone — not speech.",
    None,
    None,
    "bvs.engines.dummy:create_engine",
    None,
    Capabilities(
        ("bn", "en"),
        True,
        False,
        True,
        False,
        False,
        24000,
        500,
        30.0,
    ),
    LicenseInfo("MIT", None, "allowed", ""),
    0,
    None,
    None,
    "test-only",
)


def create_engine() -> Engine:
    from bvs.registry import _make_engine

    return _make_engine(SPEC)
