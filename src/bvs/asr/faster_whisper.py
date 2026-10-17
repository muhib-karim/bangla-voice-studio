"""Faster Whisper small; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('faster-whisper', 'asr', 'Faster Whisper small', 'Systran/faster-whisper-small', None,
    'bvs.asr.faster_whisper:create_engine', 'asr',
    Capabilities(('bn', 'en') if 'faster-whisper' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 False, False, False, True, True, None, 500, 30.0 if False else None),
    LicenseInfo('LicenseRef-Unknown', None, 'unknown', 'Model validation pending' if 'experimental' == 'experimental' else ''),
    0 if 'experimental' == 'test-only' else None, None, None, 'experimental')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
