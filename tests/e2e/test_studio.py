"""CI-only real browser workflows; removing submission/recovery breaks these tests."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from playwright.sync_api import Page

import os
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(os.getenv("BVS_E2E") != "1", reason="Browser execution is CI-only"),
]


@pytest.fixture
def studio(page: Page) -> Iterator[Page]:
    base = os.getenv("BVS_BASE_URL", "http://127.0.0.1:8000")
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console", lambda message: errors.append(message.text) if message.type == "error" else None
    )
    page.route(
        "**/*",
        lambda route: (
            route.continue_()
            if urlsplit(route.request.url).netloc == urlsplit(base).netloc
            or route.request.url.startswith("data:")
            else route.abort()
        ),
    )
    page.goto(base + "/speak")
    page.get_by_role("button", name="English", exact=True).click()
    yield page
    assert not errors, errors


def test_speech_preview_render_and_restore(studio: Page) -> None:
    page = studio
    page.get_by_label("Text", exact=True).fill("ক্ষ জ্ঞ শ্র। আজ ৳৫০ খরচ।")
    page.get_by_role("button", name="Preview reading").click()
    page.get_by_test_id("preview").get_by_text("পঞ্চাশ টাকা", exact=False).wait_for()
    page.get_by_role("button", name="Create audio", exact=True).click()
    page.get_by_test_id("job-state").filter(has_text="succeeded").wait_for(timeout=30000)
    assert "?job=" in page.url
    page.reload()
    page.get_by_test_id("job-state").filter(has_text="succeeded").wait_for()
    assert page.locator("audio").count() >= 1
    with page.expect_download() as download:
        page.get_by_role("link", name="speech.wav", exact=True).click()
    assert download.value.suggested_filename.endswith(".wav")


def test_validation_theme_mobile_and_pages(studio: Page, tmp_path: Path) -> None:
    page = studio
    page.get_by_role("button", name="Create audio", exact=True).click()
    summary = page.get_by_role("alert")
    assert summary.is_visible()
    assert summary.evaluate("(e) => e === document.activeElement")
    page.get_by_role("button", name="Dark theme").click()
    page.reload()
    assert page.locator("html").get_attribute("data-theme") == "dark"
    page.set_viewport_size({"width": 320, "height": 760})
    for name in ("Clone", "Transcribe", "Audiobook", "Engines", "Speak"):
        page.get_by_role("link", name=name, exact=True).click()
        page.get_by_role("heading", level=1).wait_for()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    screenshots = Path("screenshots")
    screenshots.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)


def test_audiobook_preview_and_render(studio: Page) -> None:
    page = studio
    page.get_by_role("link", name="Audiobook", exact=True).click()
    page.get_by_label("Title", exact=True).fill("ছোট বই")
    page.get_by_label("Text", exact=True).fill(
        "# প্রথম অধ্যায়\n\nআমি বাংলায় বলি।\n\n# দ্বিতীয় অধ্যায়\n\nআবার দেখা হবে।"
    )
    page.get_by_role("button", name="Preview chapters").click()
    page.get_by_test_id("preview").get_by_text("প্রথম অধ্যায়", exact=False).wait_for()
    page.get_by_role("button", name="Create audiobook").click()
    page.get_by_test_id("job-state").filter(has_text="succeeded").wait_for(timeout=30000)
    assert page.get_by_test_id("results").get_by_role("link").count() > 0


def test_transcribe_upload(studio: Page, tmp_path: Path) -> None:
    import wave

    audio = tmp_path / "reference.wav"
    with wave.open(str(audio), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x10" * 32000)
    page = studio
    page.get_by_role("link", name="Transcribe", exact=True).click()
    page.get_by_label("Audio file").set_input_files(audio)
    page.get_by_role("button", name="Create transcript").click()
    page.get_by_test_id("job-state").filter(has_text="succeeded").wait_for(timeout=30000)
    assert page.get_by_test_id("results").inner_text()
    assert page.get_by_test_id("demo-banner").is_visible()


def test_clone_requires_transcript_and_renders(studio: Page, tmp_path: Path) -> None:
    import wave

    audio = tmp_path / "reference.wav"
    with wave.open(str(audio), "wb") as output:
        output.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        output.writeframes(b"\x00\x10" * 72000)
    studio.get_by_role("link", name="Clone", exact=True).click()
    studio.get_by_label("Text", exact=True).fill("নতুন কথা।")
    studio.get_by_label("Reference audio", exact=True).set_input_files(audio)
    studio.get_by_role("button", name="Create audio", exact=True).click()
    assert studio.get_by_role("alert").is_visible()
    studio.get_by_label("Reference transcript", exact=True).fill("আগের কথা।")
    studio.get_by_role("button", name="Create audio", exact=True).click()
    studio.get_by_test_id("job-state").filter(has_text="succeeded").wait_for(timeout=30000)
    assert studio.get_by_role("link", name="speech.wav", exact=True).is_visible()


def test_engines_and_draft_navigation(studio: Page) -> None:
    studio.get_by_label("Text", exact=True).fill("আমার লেখা।")
    studio.get_by_role("link", name="Engines", exact=True).click()
    planned = studio.locator(".engine-row").filter(has_text="VoxCPM2")
    assert planned.get_by_text("Not published yet", exact=True).is_visible()
    assert planned.get_by_role("button", name="Download model").is_disabled()
    studio.go_back()
    assert studio.get_by_label("Text", exact=True).input_value() == "আমার লেখা।"


@pytest.mark.parametrize("width", [375, 768, 1440])
def test_responsive_keyboard_and_bengali_font(studio: Page, width: int) -> None:
    studio.set_viewport_size({"width": width, "height": 900})
    studio.get_by_role("button", name="বাংলা", exact=True).click()
    studio.get_by_label("লেখা", exact=False).fill("ক্ষ জ্ঞ শ্র — বাংলা ও English।")
    studio.evaluate("document.fonts.ready")
    assert studio.evaluate('document.fonts.check(\'18px "Noto Sans Bengali"\', "ক্ষ জ্ঞ শ্র")')
    assert studio.evaluate("document.documentElement.scrollWidth <= innerWidth")
    studio.keyboard.press("Control+Home")
    studio.locator(".skip").focus()
    studio.keyboard.press("Enter")
    assert studio.locator("#main").evaluate("(node) => node === document.activeElement")


def test_cancel_restore_and_resume_book(studio: Page) -> None:
    studio.get_by_role("link", name="Audiobook", exact=True).click()
    studio.get_by_label("Title", exact=True).fill("বাতিলের পরীক্ষা")
    studio.get_by_label("Text", exact=True).fill("# অধ্যায়\n\n" + "আমি বাংলায় কথা বলি। " * 150)
    studio.get_by_role("button", name="Create audiobook").click()
    studio.get_by_role("button", name="Cancel job").click()
    studio.get_by_test_id("job-state").filter(has_text="cancelled").wait_for(timeout=15000)
    original = studio.url
    studio.reload()
    studio.get_by_role("button", name="Resume audiobook").click()
    studio.get_by_test_id("job-state").filter(has_text="succeeded").wait_for(timeout=60000)
    assert studio.url != original
    assert "rerenders" in studio.get_by_test_id("results").inner_text()


def test_capture_labelled_demo(studio: Page) -> None:
    output = Path("screenshots")
    output.mkdir(exist_ok=True)
    studio.set_viewport_size({"width": 1280, "height": 900})
    studio.get_by_label("Text", exact=True).fill("আজ ৳৫০ খরচ। আমি বাংলায় বলি।")
    studio.evaluate("document.fonts.ready")
    studio.screenshot(path=str(output / "demo-01.png"))
    studio.get_by_role("button", name="Preview reading").click()
    studio.get_by_test_id("preview").get_by_text("পঞ্চাশ টাকা", exact=False).wait_for()
    studio.screenshot(path=str(output / "demo-02.png"))
    studio.get_by_role("button", name="Create audio", exact=True).click()
    studio.get_by_test_id("job-state").filter(has_text="succeeded").wait_for(timeout=30000)
    studio.screenshot(path=str(output / "demo-03.png"))
    studio.get_by_role("link", name="Audiobook", exact=True).click()
    studio.get_by_label("Text", exact=True).fill("# শুরু\n\nআমি বাংলায় বলি।\n\n# শেষ\n\nআবার দেখা হবে।")
    studio.get_by_role("button", name="Preview chapters").click()
    studio.get_by_test_id("preview").get_by_text("শুরু", exact=False).wait_for()
    studio.screenshot(path=str(output / "demo-04.png"))
