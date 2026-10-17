"""Indic Parler; dependencies are loaded only by load()."""

from bvs.contracts import Capabilities, Engine, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "indic-parler",
    "tts",
    "Indic Parler",
    "ai4bharat/indic-parler-tts",
    None,
    "bvs.engines.indic_parler:create_engine",
    "indic-parler",
    Capabilities(
        ("bn",),
        False,
        False,
        True,
        False,
        False,
        44100,
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


def create_engine() -> Engine:
    from bvs.registry import _make_engine

    return _make_engine(SPEC)
