import pytest

from bvs.captions import Cue, render_srt, render_vtt
from bvs.errors import BVSError


def test_golden_captions_and_empty():
    cues = (Cue(0, 300, 'বাংলা', 'tts-sentence'),)
    assert render_srt(cues) == '1\n00:00:00,000 --> 00:00:00,300\nবাংলা\n'
    assert render_vtt(cues) == 'WEBVTT\n\n00:00:00.000 --> 00:00:00.300\nবাংলা\n'
    assert render_srt(()) == ''
    assert render_vtt(()) == 'WEBVTT\n\n'


def test_hours_markup_and_invalid_clocks():
    output = render_srt((Cue(3_600_000, 3_600_300, '<script>কথা</script>\x00', 'asr-segment'),))
    assert '01:00:00,000' in output and '<script>' not in output and '\x00' not in output
    for cues in [(Cue(-1, 3, 'a', 'tts-sentence'),), (Cue(2, 1, 'a', 'tts-sentence'),), (Cue(0, 20, 'a', 'tts-sentence'), Cue(10, 30, 'b', 'tts-sentence'))]:
        with pytest.raises(BVSError):
            render_vtt(cues)
