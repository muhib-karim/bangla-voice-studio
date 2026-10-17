"""VoxCPM2 Bangla LoRA; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('voxcpm2-bn', 'tts', 'VoxCPM2 Bangla LoRA', None, None,
    'bvs.engines.voxcpm2_bn:create_engine', 'voxcpm2',
    Capabilities(('bn', 'en') if 'voxcpm2-bn' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 False, False, False, False, False, None, 500, 30.0 if False else None),
    LicenseInfo('LicenseRef-Unknown', None, 'unknown', 'Model validation pending' if 'planned' == 'experimental' else ''),
    0 if 'planned' == 'test-only' else None, None, None, 'planned')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
