"""IndicF5; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('indicf5', 'tts', 'IndicF5', 'ai4bharat/IndicF5', None,
    'bvs.engines.indicf5:create_engine', 'indicf5',
    Capabilities(('bn', 'en') if 'indicf5' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 True, True, False, False, False, 24000, 500, 30.0 if True else None),
    LicenseInfo('LicenseRef-Unknown', None, 'unknown', 'Model validation pending' if 'experimental' == 'experimental' else ''),
    0 if 'experimental' == 'test-only' else None, None, None, 'experimental')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
