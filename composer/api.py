"""Stable Python API for other programs (e.g. 음악플레이리스트-스튜디오).

The CLI is for people; this module is for code. Keep its signature stable —
callers import it by path and can't pin a version.

    from composer.api import compose
    info = compose("lofi", "/out/track01", key="D minor", seed=7, length="full")
"""
from __future__ import annotations

import os

from . import theory
from .arranger import build_composition
from .markets import get_market
from .midiwriter import write_midi
from .suno_prompt import build_suno_prompt
from .synth import render as render_wav

GENRES = sorted(theory.GENRE_PRESETS)


def compose(genre: str, out_base: str, *, key: str = "C major", tempo: int | None = None,
            seed: int | None = None, length: str = "full", market: str | None = None,
            mood: str | None = None, wav: bool = True, midi: bool = True) -> dict:
    """Compose one track and write `<out_base>.wav` / `<out_base>.mid`.

    Returns what was made, so the caller can record it as rights evidence
    (the seed + MIDI reproduce the exact same track).
    """
    comp = build_composition(genre=genre, key=key, tempo=tempo, seed=seed, length=length)
    os.makedirs(os.path.dirname(os.path.abspath(out_base)), exist_ok=True)
    out = {"genre": comp.genre, "key": comp.key, "tempo": comp.tempo, "seed": seed,
           "length": length, "seconds": round(comp.duration_seconds, 1),
           "wav": None, "mid": None}
    if wav:
        out["wav"] = f"{out_base}.wav"
        render_wav(comp, out["wav"])
    if midi:
        out["mid"] = f"{out_base}.mid"
        write_midi(comp, out["mid"])
    if market or mood:
        out["suno_prompt"] = build_suno_prompt(comp, mood, None,
                                               market=get_market(market) if market else None)
    return out
