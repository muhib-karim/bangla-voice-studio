"""MMS Bangla; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('mms', 'tts', 'MMS Bangla', 'facebook/mms-tts-ben', None,
    'bvs.engines.mms:create_engine', 'mms',
    Capabilities(('bn', 'en') if 'mms' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 False, False, False, False, False, 16000, 500, 30.0 if False else None),
    LicenseInfo('CC-BY-NC-4.0', None, 'non-commercial', 'Model validation pending' if 'experimental' == 'experimental' else ''),
    0 if 'experimental' == 'test-only' else None, None, None, 'experimental')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
