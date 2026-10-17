"""VoxCPM2 Bangla LoRA; dependencies are loaded only by load()."""

from bvs.contracts import Capabilities, Engine, EngineSpec, LicenseInfo

SPEC = EngineSpec(
    "voxcpm2-bn",
    "tts",
    "VoxCPM2 Bangla LoRA",
    None,
    None,
    "bvs.engines.voxcpm2_bn:create_engine",
    "voxcpm2",
    Capabilities(
        ("bn",),
        False,
        False,
        False,
        False,
        False,
        None,
        500,
        None,
    ),
    LicenseInfo(
        "LicenseRef-Unknown",
        None,
        "unknown",
        "",
    ),
    None,
    None,
    None,
    "planned",
)


def create_engine() -> Engine:
    from bvs.registry import _make_engine

    return _make_engine(SPEC)
