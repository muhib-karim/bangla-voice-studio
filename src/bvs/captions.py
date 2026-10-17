"""UTF-8 captions from measured synthesis units or ASR segments."""

from __future__ import annotations

import html
import re
import textwrap
from dataclasses import dataclass
from typing import Literal

from bvs.errors import BVSError


@dataclass(frozen=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str
    source: Literal["tts-sentence", "asr-segment", "asr-word-group"]


def _clock(ms: int, separator: str) -> str:
    seconds, millis = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{millis:03}"


def _render(cues: tuple[Cue, ...], *, vtt: bool) -> str:
    blocks: list[str] = []
    previous = 0
    for i, cue in enumerate(cues, 1):
        if (
            type(cue.start_ms) is not int
            or type(cue.end_ms) is not int
            or cue.start_ms < previous
            or cue.end_ms <= cue.start_ms
        ):
            raise BVSError(
                "INVALID_TIMING",
                "Caption times must be non-negative, increasing and non-overlapping",
            )
        previous = cue.end_ms
        clean = re.sub(r"<[^>]*>", "", cue.text)
        clean = "".join(c for c in clean if c >= " " or c in "\n\t")
        clean = html.escape(clean.replace("-->", "→"), quote=False)
        clean = "\n".join(
            textwrap.wrap(clean, width=42, break_long_words=False, break_on_hyphens=False)
        )
        sep = "." if vtt else ","
        clock = f"{_clock(cue.start_ms, sep)} --> {_clock(cue.end_ms, sep)}"
        blocks.append(("" if vtt else f"{i}\n") + clock + "\n" + clean)
    return ("WEBVTT\n\n" if vtt else "") + "\n\n".join(blocks) + ("\n" if blocks else "")


def render_srt(cues: tuple[Cue, ...]) -> str:
    return _render(cues, vtt=False)


def render_vtt(cues: tuple[Cue, ...]) -> str:
    return _render(cues, vtt=True)
