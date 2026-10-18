"""Chapter detection cases not covered by test_text.py (PLAN M3.2)."""

import pytest

from bvs.errors import BVSError
from bvs.text import detect_chapters

# "অধ্যায়" is typed two ways: with the precomposed YYA (U+09DF) or YA + NUKTA.
ADHYAY_PRECOMPOSED = "অধ্যা\u09df"
ADHYAY_DECOMPOSED = "অধ্যা\u09af\u09bc"


def test_word_headings_split_plain_text_and_keep_preface() -> None:
    book = "শুরুর কথা।\n\nঅধ্যায় ১\nপ্রথম লেখা।\n\nপরিচ্ছেদ ২\nদ্বিতীয় লেখা।"
    chapters = detect_chapters(book, format="txt")
    assert [c.title for c in chapters] == ["ভূমিকা", "অধ্যায় ১", "পরিচ্ছেদ ২"]
    assert [c.index for c in chapters] == [0, 1, 2]
    assert chapters[0].text == "শুরুর কথা।"
    assert chapters[1].text == "প্রথম লেখা।"
    assert chapters[2].text == "দ্বিতীয় লেখা।"


@pytest.mark.parametrize("word", [ADHYAY_PRECOMPOSED, ADHYAY_DECOMPOSED])
def test_both_unicode_spellings_of_adhyay_are_headings(word: str) -> None:
    chapters = detect_chapters(f"{word} এক\nকথা।\n\n{word} দুই\nআরও।", format="txt")
    # No text before the first heading, so no empty preface chapter.
    assert [c.title for c in chapters] == [f"{word} এক", f"{word} দুই"]


@pytest.mark.parametrize("line", ["অধ্যায় শেষ হলো।", "পরিচ্ছেদ কোথায়?"])
def test_heading_word_in_a_sentence_is_not_a_heading(line: str) -> None:
    chapters = detect_chapters(f"{line}\nকথা চলছে।", format="txt")
    assert len(chapters) == 1
    assert chapters[0].title == "অধ্যায় ১"


def test_word_headings_outrank_numbered_lines() -> None:
    chapters = detect_chapters("অধ্যায় এক\n\n১. তালিকা\n\nকথা।", format="txt")
    assert [c.title for c in chapters] == ["অধ্যায় এক"]
    assert "১. তালিকা" in chapters[0].text


def test_bare_bengali_digit_heading_takes_next_line_as_title() -> None:
    book = "৩\nনদীর গল্প\nজল বয়ে যায়।\n\n৪\nশেষ কথা\nবিদায়।"
    chapters = detect_chapters(book, format="txt")
    assert [c.title for c in chapters] == ["৩ নদীর গল্প", "৪ শেষ কথা"]
    assert chapters[0].text == "জল বয়ে যায়।"
    assert chapters[1].text == "বিদায়।"


def test_markdown_strips_front_matter_tilde_fences_and_links() -> None:
    book = (
        "---\ntitle: গোপন\n---\n# এক ##\n[লিংক](https://example.org) পড়ো।\n"
        "~~~\nhidden\n~~~\n# দুই\n**শেষ।**"
    )
    chapters = detect_chapters(book, format="md")
    assert [c.title for c in chapters] == ["এক", "দুই"]
    joined = "\n".join(c.text for c in chapters)
    assert "গোপন" not in joined
    assert "hidden" not in joined
    assert chapters[0].text == "লিংক পড়ো।"
    assert chapters[1].text == "শেষ।"


@pytest.mark.parametrize("text", ["", "   \n\n"])
def test_blank_input_has_no_chapters(text: str) -> None:
    assert detect_chapters(text, format="txt") == ()


def test_epub_is_refused() -> None:
    with pytest.raises(BVSError):
        detect_chapters("কিছু", format="epub")
