"""Conservative written-to-spoken Bangla rules; no model dependencies.

Vocabulary and cardinal composition ported from bntts/bnnorm.py (MIT).
Copyright (c) 2026 Muhib Karim. See docs/normaliser-port.md.
"""

from __future__ import annotations

import re
import unicodedata as ud
from dataclasses import dataclass
from datetime import date

NORMALISER_VERSION = "1"
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
ONES = ud.normalize(
    "NFC",
    "শূন্য এক দুই তিন চার পাঁচ ছয় সাত আট নয় দশ এগারো বারো তেরো চৌদ্দ পনেরো ষোলো সতেরো আঠারো উনিশ বিশ একুশ বাইশ তেইশ চব্বিশ পঁচিশ ছাব্বিশ সাতাশ আটাশ ঊনত্রিশ ত্রিশ একত্রিশ বত্রিশ তেত্রিশ চৌত্রিশ পঁয়ত্রিশ ছত্রিশ সাঁইত্রিশ আটত্রিশ ঊনচল্লিশ চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চুয়াল্লিশ পঁয়তাল্লিশ ছেচল্লিশ সাতচল্লিশ আটচল্লিশ ঊনপঞ্চাশ পঞ্চাশ একান্ন বাহান্ন তিপ্পান্ন চুয়ান্ন পঞ্চান্ন ছাপ্পান্ন সাতান্ন আটান্ন ঊনষাট ষাট একষট্টি বাষট্টি তেষট্টি চৌষট্টি পঁয়ষট্টি ছেষট্টি সাতষট্টি আটষট্টি ঊনসত্তর সত্তর একাত্তর বাহাত্তর তিয়াত্তর চুয়াত্তর পঁচাত্তর ছিয়াত্তর সাতাত্তর আটাত্তর ঊনআশি আশি একাশি বিরাশি তিরাশি চুরাশি পঁচাশি ছিয়াশি সাতাশি আটাশি ঊননব্বই নব্বই একানব্বই বিরানব্বই তিরানব্বই চুরানব্বই পঁচানব্বই ছিয়ানব্বই সাতানব্বই আটানব্বই নিরানব্বই",
).split()


@dataclass(frozen=True)
class TextChange:
    start: int
    end: int
    original: str
    spoken: str
    category: str


@dataclass(frozen=True)
class NormalisationResult:
    text: str
    changes: tuple[TextChange, ...]
    warnings: tuple[str, ...]


def cardinal(n: int) -> str:
    """Indian grouping, for integer values in [0, 10**15)."""
    if type(n) is not int:
        raise TypeError("cardinal requires an integer")
    if not 0 <= n < 10**15:
        raise ValueError("cardinal requires 0 <= n < 10**15")
    if n < 100:
        return ONES[n]
    parts: list[str] = []
    for size, word in ((10_000_000, "কোটি"), (100_000, "লাখ"), (1000, "হাজার")):
        if n >= size:
            parts.append(f"{cardinal(n // size)} {word}")
            n %= size
    if n >= 100:
        parts.append(ONES[n // 100] + "শো")
        n %= 100
    if n:
        parts.append(ONES[n])
    return " ".join(parts)


def year(n: int) -> str:
    """Explicit year reading; implicit text years require a year context."""
    if type(n) is not int:
        raise TypeError("year requires an integer")
    if 1100 <= n <= 1999:
        hi, lo = divmod(n, 100)
        return ONES[hi] + "শো" + (" " + ONES[lo] if lo else "")
    return cardinal(n)


def _digits(value: str) -> str:
    return " ".join(ONES[int(c)] for c in value)


def _number(value: str, *, contextual_year: bool = False) -> str:
    sign = ""
    if value[:1] in ("+", "-"):
        sign = "প্লাস " if value[0] == "+" else "মাইনাস "
        value = value[1:]
    whole, dot, fraction = value.partition(".")
    if "," in whole and not (
        re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+", whole)
        or re.fullmatch(r"[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}", whole)
    ):
        raise ValueError("malformed digit grouping")
    whole = whole.replace(",", "")
    if len(whole.lstrip("0")) > 15 or int(whole) >= 10**15:
        raise ValueError("number exceeds supported range")
    spoken = (
        _digits(whole)
        if len(whole) > 1 and whole[0] == "0"
        else (year(int(whole)) if contextual_year else cardinal(int(whole)))
    )
    if dot:
        spoken += " দশমিক " + _digits(fraction)
    return sign + spoken


_MONTHS = "জানুয়ারি ফেব্রুয়ারি মার্চ এপ্রিল মে জুন জুলাই আগস্ট সেপ্টেম্বর অক্টোবর নভেম্বর ডিসেম্বর".split()
_ORD_WORDS = "প্রথম দ্বিতীয় তৃতীয় চতুর্থ পঞ্চম ষষ্ঠ সপ্তম অষ্টম নবম দশম".split()
_ORDINALS = dict(
    zip(["1ম", "2য়", "3য়", "4র্থ", "5ম", "6ষ্ঠ", "7ম", "8ম", "9ম", "10ম"], _ORD_WORDS, strict=True)
)
_ORDINALS.update({"2য়": "দ্বিতীয়", "3য়": "তৃতীয়"})
_ORDINALS = {ud.normalize("NFC", k): ud.normalize("NFC", v) for k, v in _ORDINALS.items()}
_ABBREVIATIONS = {
    "ডা.": "ডাক্তার",
    "ড.": "ডক্টর",
    "মো.": "মোহাম্মদ",
    "প্রফে.": "প্রফেসর",
    "Dr.": "ডক্টর",
    "Mr.": "মিস্টার",
}
_D = "[0-9০-৯]"
_N = rf"[+-]?{_D}+(?:,{_D}+)*(?:\.{_D}+)?"
# Master search consumes a token once. Invalid structured matches remain protected.
_PATTERNS = [
    ("code", r"```[\s\S]*?(?:```|$)|`[^`\n]*(?:`|$)"),
    ("protected", r"(?:https?://|www\.)[^\s<>]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ("currency", rf"(?:৳|(?i:Tk\.?|BDT)(?![A-Za-z]))[ \t]*{_N}|{_N}[ \t]*(?:টাকা|(?i:Tk|BDT)\b)"),
    (
        "phone",
        rf"(?<![\w])(?:\+880|\+৮৮০)[ \t]*{_D}+(?:[ -]{_D}+)*|(?<![\w])(?:01|০১){_D}+(?:[ -]{_D}+)*",
    ),
    ("date", rf"(?<![\w]){_D}{{1,4}}[-/]{_D}{{1,2}}[-/]{_D}{{1,4}}(?![\w])"),
    ("time", rf"(?<![\w]){_D}+:{_D}+(?::{_D}+)?(?![\w])"),
    ("ordinal", rf"(?<![\w]){_D}+(?:তম|র্থ|ষ্ঠ|[মযয়য়]+|(?i:st|nd|rd|th))(?![\w])"),
    ("protected", r"[A-Za-z_][A-Za-z_0-9.+-]*[0-9][A-Za-z_0-9.+-]*|[0-9]+(?:\.[0-9]+){2,}"),
    ("abbreviation", r"(?<!\w)(?:ডা\.|ড\.|মো\.|প্রফে\.|Dr\.|Mr\.)(?=[ \t]+[^\W\d_])"),
    ("number", rf"(?<![\w]){_N}(?:[ \t]*%)?(?![\w])"),
]
# Duplicate category names get unique regex group names.
_TOKEN = re.compile("|".join(f"(?P<t{i}>{pattern})" for i, (_, pattern) in enumerate(_PATTERNS)))


def protected_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Token spans sentence/chunk parsers must not split."""
    return tuple(
        (m.start(), m.end())
        for m in _TOKEN.finditer(text)
        if _PATTERNS[int((m.lastgroup or "t0")[1:])][0] != "number"
    )


def _replacement(category: str, token: str, following: str) -> str:
    value = token.translate(_BN_DIGITS)
    if category in ("protected", "code"):
        return token
    if category == "phone":
        compact = re.sub(r"[ -]", "", value)
        if compact.startswith("+880"):
            local = compact[4:]
            if len(local) != 10 or not local.startswith("1"):
                raise ValueError("invalid international phone")
            return "প্লাস আট আট শূন্য, " + ", ".join(
                _digits(s) for s in (local[:4], local[4:7], local[7:])
            )
        if len(compact) != 11 or not compact.startswith("01"):
            raise ValueError("invalid domestic phone")
        return ", ".join(_digits(s) for s in (compact[:5], compact[5:8], compact[8:]))
    if category == "date":
        fields = re.split("[-/]", value)
        if len(fields[0]) == 4 and "-" in value:
            y, mo, day = map(int, fields)
        else:
            day, mo, y = map(int, fields)
            if len(fields[-1]) != 4:
                raise ValueError("date needs four-digit year")
        date(y, mo, day)
        return f"{cardinal(day)} {_MONTHS[mo - 1]} {year(y)}"
    if category == "currency":
        amount = re.sub(r"৳|(?i:Tk\.?|BDT)|টাকা|[ \t]", "", value)
        whole, dot, frac = amount.partition(".")
        if len(frac) > 2:
            raise ValueError("money has more than two fractional digits")
        out = _number(whole) + " টাকা"
        if dot and int(frac):
            out += " " + cardinal(int(frac.ljust(2, "0"))) + " পয়সা"
        return out
    if category == "time":
        fields = value.split(":")
        if len(fields) != 2 or len(fields[0]) > 2 or len(fields[1]) != 2:
            raise ValueError("invalid clock token")
        h, minute = map(int, fields)
        if h > 23 or minute > 59:
            raise ValueError("invalid clock range")
        return cardinal(h) + "টা" + (" " + cardinal(minute) if minute else "")
    if category == "ordinal":
        if value in _ORDINALS:
            return _ORDINALS[value]
        english = re.fullmatch(r"(10|[1-9])(st|nd|rd|th)", value, re.I)
        if english:
            n = int(english[1])
            expected = {1: "st", 2: "nd", 3: "rd"}.get(n, "th")
            return (
                ud.normalize("NFC", _ORD_WORDS[n - 1]) if english[2].lower() == expected else token
            )
        if value.endswith("তম"):
            return _number(value[:-2]) + "তম"
        return token
    if category == "abbreviation":
        return _ABBREVIATIONS[token]
    if value.endswith("%"):
        return _number(value[:-1].rstrip()) + " শতাংশ"
    return _number(
        value, contextual_year=bool(re.match(r"[ \t]+(?:সালে|সাল|খ্রিস্টাব্দ)(?!\w)", following))
    )


def _nfc_map(text: str) -> tuple[str, list[tuple[int, int]]]:
    pieces: list[str] = []
    offsets: list[tuple[int, int]] = []
    start = 0
    for i in range(1, len(text) + 1):
        if i == len(text) or not ud.combining(text[i]):
            piece = ud.normalize("NFC", text[start:i])
            pieces.append(piece)
            offsets.extend([(start, i)] * len(piece))
            start = i
    return "".join(pieces), offsets


def normalise_with_report(text: str) -> NormalisationResult:
    """Rewrite recognized spans once, preserving original codepoint offsets."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    source, offsets = _nfc_map(text)
    parts: list[str] = []
    changes: list[TextChange] = []
    warnings: list[str] = []
    cursor = 0
    for match in _TOKEN.finditer(source):
        start, end = match.span()
        token = match[0]
        category = _PATTERNS[int((match.lastgroup or "t0")[1:])][0]
        try:
            spoken = ud.normalize("NFC", _replacement(category, token, source[end:]))
        except ValueError as exc:
            spoken = token
            warnings.append(f"{category}: {exc} at {offsets[start][0]}")
        parts.extend((source[cursor:start], spoken))
        if spoken != token:
            a, b = offsets[start][0], offsets[end - 1][1]
            changes.append(TextChange(a, b, text[a:b], spoken, category))
        cursor = end
    parts.append(source[cursor:])
    return NormalisationResult(ud.normalize("NFC", "".join(parts)), tuple(changes), tuple(warnings))


def normalise(text: str) -> str:
    return normalise_with_report(text).text
