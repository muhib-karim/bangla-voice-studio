"""MMS Bangla; dependencies are loaded only by load()."""

from bvs.contracts import Capabilities, Engine, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "mms",
    "tts",
    "MMS Bangla",
    "facebook/mms-tts-ben",
    None,
    "bvs.engines.mms:create_engine",
    "mms",
    Capabilities(
        ("bn",),
        False,
        False,
        False,
        False,
        False,
        16000,
        500,
        None,
    ),
    LicenseInfo(
        "CC-BY-NC-4.0",
        None,
        "non-commercial",
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
