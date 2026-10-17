"""Demo tone — not speech.; dependencies are loaded only by load()."""
from bvs.contracts import Capabilities, EngineSpec, LicenseInfo
SPEC = EngineSpec('dummy', 'tts', 'Demo tone — not speech.', None, None,
    'bvs.engines.dummy:create_engine', None,
    Capabilities(('bn', 'en') if 'dummy' in ('dummy', 'fake-asr', 'omnivoice', 'faster-whisper') else ('bn',),
                 True, False, True, False, False, 24000, 500, 30.0 if True else None),
    LicenseInfo('MIT', None, 'allowed', 'Model validation pending' if 'test-only' == 'experimental' else ''),
    0 if 'test-only' == 'test-only' else None, None, None, 'test-only')

def create_engine():
    from bvs.registry import _make_engine
    return _make_engine(SPEC)
