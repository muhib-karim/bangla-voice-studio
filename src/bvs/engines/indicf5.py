"""IndicF5; dependencies are loaded only by load()."""

from bvs.contracts import Capabilities, Engine, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "indicf5",
    "tts",
    "IndicF5",
    "ai4bharat/IndicF5",
    None,
    "bvs.engines.indicf5:create_engine",
    "indicf5",
    Capabilities(
        ("bn",),
        True,
        True,
        False,
        False,
        False,
        24000,
        500,
        30.0,
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
