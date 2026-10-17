"""CI-only real browser workflows; removing submission/recovery breaks these tests."""
import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv('BVS_E2E') != '1', reason='Browser execution is CI-only')]


@pytest.fixture
def studio(page):
    base = os.getenv('BVS_BASE_URL', 'http://127.0.0.1:8000')
    page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) or route.request.url.startswith('data:') else route.abort())
    page.goto(base + '/speak')
    page.get_by_role('button', name='English', exact=True).click()
    return page


def test_speech_preview_render_and_restore(studio):
    page = studio
    page.get_by_label('Text', exact=True).fill('ক্ষ জ্ঞ শ্র। আজ ৳৫০ খরচ।')
    page.get_by_role('button', name='Preview reading').click()
    page.get_by_test_id('preview').get_by_text('পঞ্চাশ টাকা', exact=False).wait_for()
    page.get_by_role('button', name='Create audio', exact=True).click()
    page.get_by_test_id('job-state').filter(has_text='succeeded').wait_for(timeout=30000)
    assert '?job=' in page.url
    page.reload()
    page.get_by_test_id('job-state').filter(has_text='succeeded').wait_for()
    assert page.locator('audio').count() >= 1
    with page.expect_download() as download:
        page.get_by_role('link', name='speech.wav', exact=True).click()
    assert download.value.suggested_filename.endswith('.wav')


def test_validation_theme_mobile_and_pages(studio, tmp_path: Path):
    page = studio
    page.get_by_role('button', name='Create audio', exact=True).click()
    summary = page.get_by_role('alert')
    assert summary.is_visible()
    assert summary.evaluate('(e) => e === document.activeElement')
    page.get_by_role('button', name='Dark theme').click()
    page.reload()
    assert page.locator('html').get_attribute('data-theme') == 'dark'
    page.set_viewport_size({'width': 320, 'height': 760})
    for name in ('Clone', 'Transcribe', 'Audiobook', 'Engines', 'Speak'):
        page.get_by_role('link', name=name, exact=True).click()
        page.get_by_role('heading', level=1).wait_for()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(tmp_path / 'mobile.png'), full_page=True)


def test_audiobook_preview_and_render(studio):
    page = studio
    page.get_by_role('link', name='Audiobook', exact=True).click()
    page.get_by_label('Title', exact=True).fill('ছোট বই')
    page.get_by_label('Text', exact=True).fill('# প্রথম অধ্যায়\n\nআমি বাংলায় বলি।\n\n# দ্বিতীয় অধ্যায়\n\nআবার দেখা হবে।')
    page.get_by_role('button', name='Preview chapters').click()
    page.get_by_test_id('preview').get_by_text('প্রথম অধ্যায়', exact=False).wait_for()
    page.get_by_role('button', name='Create audiobook').click()
    page.get_by_test_id('job-state').filter(has_text='succeeded').wait_for(timeout=30000)
    assert page.get_by_test_id('results').get_by_role('link').count() > 0


def test_transcribe_upload(studio, tmp_path: Path):
    import wave
    audio = tmp_path / 'reference.wav'
    with wave.open(str(audio), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b'\x00\x10' * 32000)
    page = studio
    page.get_by_role('link', name='Transcribe', exact=True).click()
    page.get_by_label('Audio file').set_input_files(audio)
    page.get_by_role('button', name='Create transcript').click()
    page.get_by_test_id('job-state').filter(has_text='succeeded').wait_for(timeout=30000)
    assert page.get_by_test_id('results').inner_text()
    assert page.get_by_test_id('demo-banner').is_visible()
