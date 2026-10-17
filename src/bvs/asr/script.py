"""Script checks for recognizer output."""

from __future__ import annotations

_BENGALI = range(0x0980, 0x0A00)
_DEVANAGARI = range(0x0900, 0x0980)

DEVANAGARI_WARNING = (
    "The recognizer returned Devanagari script for Bangla audio. "
    "Whisper small often does this; a larger Whisper model is more likely "
    "to write Bengali script."
)


def script_counts(text: str) -> tuple[int, int]:
    """Return (Bengali, Devanagari) letter counts in ``text``."""
    bengali = devanagari = 0
    for ch in text:
        code = ord(ch)
        if code in _BENGALI:
            bengali += 1
        elif code in _DEVANAGARI:
            devanagari += 1
    return bengali, devanagari


def bangla_script_warnings(text: str, language: str | None) -> tuple[str, ...]:
    """Warn when Bangla was requested but the transcript is mostly Devanagari."""
    if language != "bn":
        return ()
    bengali, devanagari = script_counts(text)
    if devanagari > bengali:
        return (DEVANAGARI_WARNING,)
    return ()
