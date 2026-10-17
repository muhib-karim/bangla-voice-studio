# Bangla normalizer port

Upstream: `bangla-tts-bench`, commit `c0d49dcb9c717408d3181baaaa0f80454f489d96`.
Source: `bntts/bnnorm.py`; tests: `tests/test_bnnorm.py`; data: `data/testset.tsv`.
License: MIT, Copyright (c) 2026 Muhib Karim. PLAN.md records inspection provenance.

| Upstream file | SHA-256 |
|---|---|
| `bntts/bnnorm.py` | `b7bf7501bb1e6f4dc80e85c5be8492bc24587448c9aa43ee2c3677ae25c919dd` |
| `tests/test_bnnorm.py` | `86a752f55cc575024e141fbb9416e5b6a546ba047e9db3394f7ef2bfa2d7fffb` |
| `data/testset.tsv` | `201b12cdde68d0d7ad7321b278c0024c7cfe6f85bffbf7540a6ee98c8c6aa03f` |

Retained: 0–99 vocabulary, Indian grouping, `cardinal`, `year`, and the public
`normalise` spelling. Tests use local fixtures; no sibling checkout is required.

Intentional changes: contextual year reading, strict helper bounds, grouped phones
including +880, validated Gregorian dates/times, currency precision checks,
whole-token ordinals/abbreviations, protected mixed-script tokens, and warnings for
invalid structured tokens. Reports use original codepoint offsets. Output is NFC.

The 50-row reference fixture keeps its original expected text. Named test migrations
preserve Banglish unchanged and group phone digits in row `d03`: the spoken phone
is `শূন্য এক সাত এক দুই, তিন চার পাঁচ, ছয় সাত আট` instead of the old ungrouped
digit reading. Ordinary four-digit quantities use cardinal reading; explicit
`year(1971)` and `১৯৭১ সালে` keep `উনিশশো একাত্তর`.

Native Bangla fixture/listening review is still required before release. Mechanical
24-hour readings such as `শূন্যটা` follow PLAN.md; no morning/evening inference is
made. The benchmark's original scoring normalizer is unchanged.
