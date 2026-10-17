"""Simulated fixture transcript; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('fake-asr', 'asr', 'Simulated fixture transcript', None, None,
    'bvs.asr.fake:create_engine', None,
    Capabilities(('bn', 'en') if 'fake-asr' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 False, False, False, True, True, None, 500, 30.0 if False else None),
    LicenseInfo('MIT', None, 'allowed', 'Model validation pending' if 'test-only' == 'experimental' else ''),
    0 if 'test-only' == 'test-only' else None, None, None, 'test-only')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
