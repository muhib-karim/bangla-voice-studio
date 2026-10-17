"""OmniVoice; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('omnivoice', 'tts', 'OmniVoice', 'k2-fsa/OmniVoice', None,
    'bvs.engines.omnivoice:create_engine', 'omnivoice',
    Capabilities(('bn', 'en') if 'omnivoice' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 True, True, False, False, False, 24000, 500, 30.0 if True else None),
    LicenseInfo('LicenseRef-Unknown', None, 'unknown', 'Model validation pending' if 'experimental' == 'experimental' else ''),
    0 if 'experimental' == 'test-only' else None, None, None, 'experimental')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
