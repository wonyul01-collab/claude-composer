"""Lyric helpers.

Claude Composer does not synthesize a singing voice -- no pure-Python
approach can do that convincingly. When this project runs *inside*
Claude Code, Claude should write real lyrics itself (it is far better at
that than any template) and hand them to render_song() as a `lyrics`
dict. This module gives:

1. `syllable_budget()` -- how many melody notes each section has, as a
   rough guide for how many syllables a lyric line should carry.
2. `placeholder_lyrics()` -- plain filler text for a quick instrumental
   preview when nobody has supplied real lyrics yet.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .arranger import Composition


@dataclass
class LyricSet:
    sections: dict[str, list[str]] = field(default_factory=dict)


PLACEHOLDER_LINES = {
    "verse": ["(여기에 첫 소절 가사를 적어보세요)", "(당신의 이야기를 한 줄 더)"],
    "chorus": ["(후렴 - 가장 기억에 남는 한 줄)", "(다시 한 번 반복되는 문장)"],
    "bridge": ["(분위기를 바꾸는 한 줄)"],
    "intro": [],
    "outro": ["(마무리하는 한 줄)"],
}


def syllable_budget(comp: Composition) -> dict[str, list[int]]:
    """Melody note count per section occurrence, as a syllable-count hint."""
    budget: dict[str, list[int]] = {}
    for sec in comp.sections:
        start_beat = sec.start_bar * comp.beats_per_bar
        end_beat = (sec.start_bar + sec.bars) * comp.beats_per_bar
        count = sum(1 for n in comp.melody if start_beat <= n.start < end_beat)
        budget.setdefault(sec.name, []).append(count)
    return budget


def placeholder_lyrics(comp: Composition) -> LyricSet:
    sections: dict[str, list[str]] = {}
    for sec in comp.sections:
        sections.setdefault(sec.name, PLACEHOLDER_LINES.get(sec.name, []))
    return LyricSet(sections=sections)


def load_lyrics_json(data: dict) -> LyricSet:
    """data: {"verse": ["line1", "line2"], "chorus": [...], ...}"""
    return LyricSet(sections={k: list(v) for k, v in data.items()})
