"""Sentence units and conservative chapter detection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from bvs.errors import BVSError
from bvs.normalise import protected_spans

CHUNKER_VERSION = '1'


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    text: str


def split_sentences(text: str) -> tuple[str, ...]:
    protected = bytearray(len(text))
    for start, end in protected_spans(text):
        # A URL's final full stop belongs to sentence punctuation.
        if text[start:end].startswith(('http', 'www.')):
            end = len(text[:end].rstrip('.!?।'))
        protected[start:end] = b'\1' * (end-start)
    for match in re.finditer(r'[0-9০-৯]\.[0-9০-৯]', text):
        protected[match.start()+1] = 1
    units: list[str] = []
    start, i = 0, 0
    while i < len(text):
        if not protected[i] and text[i] in '।?!.' :
            end = i+1
            while end < len(text) and text[end] in '।?!.\"\'”’»)':
                end += 1
            if text[start:end].strip():
                units.append(text[start:end].strip())
            start = i = end
        elif text[i:i+2] == '\n\n':
            if text[start:i].strip():
                units.append(text[start:i].strip())
            i += 2
            start = i
        else:
            i += 1
    if text[start:].strip():
        units.append(text[start:].strip())
    return tuple(units)


def chunk_sentence(text: str, *, max_chars: int) -> tuple[str, ...]:
    if max_chars < 1:
        raise BVSError('INVALID_INPUT', 'max_chars must be positive')
    # Whitespace boundaries keep virama/ZWJ/combining clusters and URLs intact.
    words = text.split()
    result: list[str] = []
    current = ''
    for word in words:
        if len(word) > max_chars:
            raise BVSError('TEXT_TOO_LONG', 'An indivisible token exceeds max_chars; shorten the token or raise the limit')
        candidate = f'{current} {word}' if current else word
        if len(candidate) > max_chars:
            result.append(current)
            current = word
        else:
            current = candidate
    if current:
        result.append(current)
    return tuple(result)


def detect_chapters(text: str, *, format: Literal['txt', 'md', 'epub'] = 'txt') -> tuple[Chapter, ...]:
    if format == 'epub':
        raise BVSError('UNSUPPORTED_MEDIA', 'EPUB import is not available; use UTF-8 text or Markdown')
    if format == 'md':
        text = re.sub(r'\A---\s*\n.*?\n---\s*(?:\n|$)', '', text, flags=re.S)
        text = re.sub(r'```[^\n]*\n.*?(?:```|\Z)|~~~[^\n]*\n.*?(?:~~~|\Z)', '', text, flags=re.S)
    lines = text.splitlines()
    candidates: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        value = line.strip()
        markdown = re.fullmatch(r'(#{1,6})\s+(.+?)(?:\s+#+)?', value) if format == 'md' else None
        if markdown:
            candidates.append((i, markdown[2], len(markdown[1])))
        elif re.match(r'^(?:অধ্যায়|অধ্যায়|পরিচ্ছেদ)\s+\S', value) and len(value) <= 120 and not value.endswith(('।', '?', '!')):
            candidates.append((i, value, 1))
        elif (i == 0 or not lines[i-1].strip()) and len(value) <= 120 and not value.endswith(('।', '?', '!', '.')):
            if re.match(r'^[0-9০-৯]+[.)]\s+\S', value) and (i+1 == len(lines) or not lines[i+1].strip()):
                candidates.append((i, value, 2))
            elif re.fullmatch(r'[0-9০-৯]+', value) and i+1 < len(lines) and lines[i+1].strip():
                candidates.append((i, value+' '+lines[i+1].strip(), 2))
    if candidates:
        strongest = min(c[2] for c in candidates)
        candidates = [c for c in candidates if c[2] == strongest]
    chapters: list[Chapter] = []
    boundaries = [(-1, 'ভূমিকা' if candidates else 'অধ্যায় ১', 0), *candidates, (len(lines), '', 0)]
    for (start, title, _), (end, _, _) in zip(boundaries, boundaries[1:]):
        body_start = start+1
        if start >= 0 and re.fullmatch(r'[0-9০-৯]+', lines[start].strip()):
            body_start += 1
        body = '\n'.join(lines[body_start:end]).strip()
        if format == 'md':
            body = re.sub(r'^#{1,6}\s+', '', body, flags=re.M)
            body = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', body)
            body = body.replace('**', '').replace('__', '')
        if body:
            chapters.append(Chapter(len(chapters), title, body))
    return tuple(chapters)
