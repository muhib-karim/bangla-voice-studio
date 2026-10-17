"""Reject partial rewrites, incorrect numeric composition and lost punctuation."""
import csv
from pathlib import Path
import unicodedata as ud
import pytest
from bvs.normalise import cardinal, normalise, normalise_with_report

FIXTURES = Path(__file__).parents[1] / 'fixtures'
with (FIXTURES / 'normaliser_cases.tsv').open() as stream:
    CASES = list(csv.DictReader(stream, delimiter='\t'))
with (FIXTURES / 'cardinals.tsv').open() as stream:
    WORDS = [(int(n), w) for n, w in csv.reader(stream, delimiter='\t')]


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'] + '-' + c['category'])
def test_normative_cases(case):
    assert normalise(case['text']) == ud.normalize('NFC', case['spoken'])


@pytest.mark.parametrize('n,spoken', WORDS)
def test_all_base_cardinals(n, spoken):
    assert cardinal(n) == ud.normalize('NFC', spoken)


@pytest.mark.parametrize('n', [-1, 10**15, True, 1.5, '2'])
def test_cardinal_rejects_invalid_domain(n):
    with pytest.raises((TypeError, ValueError)):
        cardinal(n)


@pytest.mark.parametrize('token', ['1,23,45', '৳1.234', '24:00', '31/02/2026', '0171234567', '1000000000000000'])
def test_invalid_structured_tokens_are_preserved_and_warn(token):
    report = normalise_with_report(token)
    assert report.text == token
    assert report.warnings


def test_nonstring_is_rejected():
    with pytest.raises(TypeError):
        normalise(12)
