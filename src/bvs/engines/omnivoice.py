"""OmniVoice; dependencies are loaded only by load()."""

from bvs.contracts import Capabilities, Engine, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "omnivoice",
    "tts",
    "OmniVoice",
    "k2-fsa/OmniVoice",
    None,
    "bvs.engines.omnivoice:create_engine",
    "omnivoice",
    Capabilities(
        ("bn", "en"),
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
