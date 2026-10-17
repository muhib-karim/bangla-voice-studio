"""Port regressions: vocabulary loss, accidental transliteration, phone grouping."""

import csv
import unicodedata as ud
from pathlib import Path

import pytest

from bvs.normalise import cardinal, normalise, year

FIXTURES = Path(__file__).parents[1] / "fixtures"
with (FIXTURES / "normaliser_reference.tsv").open() as stream:
    ROWS = list(csv.DictReader(stream, delimiter="\t"))


def test_reference_inventory() -> None:
    assert len(ROWS) == len({r["id"] for r in ROWS}) == 50
    assert {r["category"] for r in ROWS} == {
        "news",
        "conversational",
        "numbers",
        "conjuncts",
        "banglish",
    }


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["id"])
def test_local_reference_with_named_migrations(row: dict[str, str]) -> None:
    expected = row["spoken"]
    if row["category"] == "banglish":  # preserve-banglish-v1
        expected = row["text"]
    if row["id"] == "d03":  # grouped-phone-v1
        expected = "আমার নম্বর শূন্য এক সাত এক দুই, তিন চার পাঁচ, ছয় সাত আট।"
    assert normalise(row["text"]) == ud.normalize("NFC", expected)


@pytest.mark.parametrize(
    "n,spoken",
    [(100, "একশো"), (1250, "এক হাজার দুইশো পঞ্চাশ"), (10**7, "এক কোটি"), (10**14, "এক কোটি কোটি")],
)
def test_magnitude_boundaries(n: int, spoken: str) -> None:
    assert cardinal(n) == ud.normalize("NFC", spoken)


def test_explicit_year() -> None:
    assert year(1971) == "উনিশশো একাত্তর"
