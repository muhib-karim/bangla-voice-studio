from pathlib import Path
import numpy as np
import pytest
from bvs.contracts import RuntimeConfig, RunContext, SynthesisRequest, ASRRequest
from bvs.errors import BVSError
from bvs.registry import create_tts, create_asr, list_engines
from bvs.media import write_wav, read_wav, inspect_wav, concatenate_wav

CTX = RunContext(lambda p: None, lambda: False)

def test_dummy_deterministic_frames_and_voice(tmp_path: Path) -> None:
    engine = create_tts('dummy')
    engine.load(RuntimeConfig(tmp_path, tmp_path, None, None), CTX)
    a = engine.synthesize(SynthesisRequest('ক খ'), output_path=tmp_path/'a.wav', context=CTX)
    b = engine.synthesize(SynthesisRequest('ক খ'), output_path=tmp_path/'b.wav', context=CTX)
    c = engine.synthesize(SynthesisRequest('ক খ', voice_description='low'), output_path=tmp_path/'c.wav', context=CTX)
    assert a.audio.frames == 4800
    assert a.audio.sha256 == b.audio.sha256 != c.audio.sha256
    assert a.audio.sample_rate_hz == 24000
    with pytest.raises(BVSError):
        engine.synthesize(SynthesisRequest(' '), output_path=tmp_path/'empty.wav', context=CTX)
    engine.unload()
    engine.unload()

def test_pcm_validation_and_streaming_concat(tmp_path: Path) -> None:
    a = write_wav(tmp_path/'a.wav', np.array([0., .5, -.5], dtype=np.float32), 24000)
    joined = concatenate_wav([a.path, a.path], tmp_path/'j.wav', pause_frames=2)
    assert joined.frames == 8
    data, rate = read_wav(joined.path)
    assert rate == 24000
    assert data.tolist() == [0., .5, -.5, 0., 0., 0., .5, -.5]
    a.path.write_bytes(a.path.read_bytes()[:-1])
    with pytest.raises(BVSError, match='truncated'):
        inspect_wav(a.path)
    with pytest.raises(BVSError):
        write_wav(tmp_path/'bad.wav', np.array([np.nan]), 24000)

def test_fake_silence_and_bounded_timestamps(tmp_path: Path) -> None:
    p = tmp_path/'silence.wav'
    write_wav(p, np.zeros(2400, dtype=np.float32), 24000)
    engine = create_asr('fake-asr')
    engine.load(RuntimeConfig(tmp_path, tmp_path, None, None), CTX)
    result = engine.transcribe(ASRRequest(p), context=CTX)
    assert result.text == '' and result.segments == () and result.warnings
    write_wav(p, np.ones(2400, dtype=np.float32)*.1, 24000)
    result = engine.transcribe(ASRRequest(p), context=CTX)
    assert result.segments[0].end_seconds <= .1
    assert result.segments[0].words[0].end_seconds <= .1

def test_registry_discovery_and_planned_guard(tmp_path: Path) -> None:
    ids = [s.id for s in list_engines()]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    with pytest.raises(BVSError) as exc:
        create_tts('voxcpm2-bn').load(RuntimeConfig(tmp_path,tmp_path,None,None), CTX)
    assert exc.value.code == 'ENGINE_UNAVAILABLE'
