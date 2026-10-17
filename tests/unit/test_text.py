import unicodedata

import pytest

from bvs.errors import BVSError
from bvs.text import chunk_sentence, detect_chapters, split_sentences


def test_sentence_boundaries_and_protected_tokens():
    assert split_sentences('ডা. রহমান ৩.১৪ বললেন। “হ্যাঁ?!” তারপর!\n\nশেষ') == ('ডা. রহমান ৩.১৪ বললেন।', '“হ্যাঁ?!”', 'তারপর!', 'শেষ')
    assert split_sentences('Visit https://example.org/v2. Next. End!') == ('Visit https://example.org/v2.', 'Next.', 'End!')
    assert split_sentences('') == ()


def test_chunks_bound_length_and_preserve_combining_sequences():
    text = 'বাংলা ক্ষতি হয় না এমন একটি কথা।'
    chunks = chunk_sentence(text, max_chars=12)
    assert ' '.join(chunks) == text
    assert all(len(c) <= 12 and not unicodedata.combining(c[0]) for c in chunks)
    with pytest.raises(BVSError, match='indivisible'):
        chunk_sentence('https://example.org/long', max_chars=10)


def test_chapters_prefer_h1_keep_preface_and_exclude_code():
    book = 'ভূমিকা।\n\n# শুরু\nকথা।\n## অংশ\nআরও।\n```python\nsecret=1\n```\n# শেষ\nবিদায়।'
    chapters = detect_chapters(book, format='md')
    assert [c.title for c in chapters] == ['ভূমিকা', 'শুরু', 'শেষ']
    assert 'secret' not in chapters[1].text
    assert 'আরও' in chapters[1].text
    assert detect_chapters('সাধারণ লেখা।', format='txt')[0].title == 'অধ্যায় ১'


def test_numbered_headings_require_blank_separation():
    chapters = detect_chapters('১. সূচনা\n\nকথা।\n\n2) শেষ\n\nআরও।', format='txt')
    assert [c.title for c in chapters] == ['১. সূচনা', '2) শেষ']
    assert len(detect_chapters('কথা\n১. একটি তালিকা\n২. আরেকটি', format='txt')) == 1
