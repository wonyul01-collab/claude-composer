"""Composition engine: turns (genre, key, tempo, structure) into a
Composition of note events for melody, bass, chord pad, and drums.

Uses a constrained weighted-random ("Markov-ish") walk for the melody:
each note is chosen from nearby scale/chord tones, weighted toward small
steps from the previous note, which is what keeps generated melodies
singable instead of random noise.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import theory
from .theory import Chord, GenrePreset, build_chord, get_preset

BEATS_PER_BAR = 4

SECTION_BARS = {
    "intro": 4, "verse": 8, "chorus": 8, "bridge": 4, "outro": 4,
}
DEFAULT_STRUCTURE = ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"]
SHORT_STRUCTURE = ["intro", "verse", "chorus", "outro"]

BASS_STYLE_BY_GENRE = {
    "lofi": "root_fifth", "pop": "root_fifth", "edm": "four_on_floor",
    "jazz": "walk", "cinematic": "sustain", "acoustic": "root_fifth",
    "citypop": "funk", "jpop": "root_fifth", "kpop": "four_on_floor",
}
# (beat_offset, chord_tone_index | 'approach', duration)
BASS_STYLES = {
    "sustain": [(0.0, 0, 4.0)],
    "four_on_floor": [(0.0, 0, 1.0), (1.0, 0, 1.0), (2.0, 0, 1.0), (3.0, 0, 1.0)],
    "root_fifth": [(0.0, 0, 2.0), (2.0, 2, 2.0)],
    "walk": [(0.0, 0, 1.0), (1.0, 1, 1.0), (2.0, 2, 1.0), (3.0, "approach", 1.0)],
    "funk": [(0.0, 0, 0.5), (0.75, 2, 0.5), (1.5, 0, 0.5), (2.5, 1, 0.5), (3.0, 2, 0.5), (3.5, 0, 0.5)],
}


@dataclass
class NoteEvent:
    start: float               # beats from song start
    dur: float                  # beats
    pitch: int = -1              # MIDI note number (unused for drum hits)
    vel: int = 90
    drum: str | None = None      # set for drum-track events: 'kick'/'snare'/'hihat'/'perc'


@dataclass
class Section:
    name: str
    start_bar: int
    bars: int
    chord_degrees: list[int]


@dataclass
class Composition:
    genre: str
    key: str
    tempo: int
    beats_per_bar: int
    total_bars: int
    sections: list[Section]
    melody: list[NoteEvent] = field(default_factory=list)
    bass: list[NoteEvent] = field(default_factory=list)
    chords_track: list[NoteEvent] = field(default_factory=list)
    drums: list[NoteEvent] = field(default_factory=list)
    lead_voice: str = "pluck"
    bass_voice: str = "synthbass"
    chord_voice: str = "pad"

    @property
    def total_beats(self) -> float:
        return self.total_bars * self.beats_per_bar

    @property
    def duration_seconds(self) -> float:
        return self.total_beats * 60.0 / self.tempo


def _parse_key_mode(key: str) -> tuple[int, str | None]:
    parts = key.strip().split()
    root = parts[0].upper()
    if root not in theory.NOTE_INDEX:
        raise ValueError(f"Unknown key root: {key!r}")
    root_pc = theory.NOTE_INDEX[root]
    rest = " ".join(parts[1:]).lower()
    if "min" in rest:
        return root_pc, "natural_minor"
    if "maj" in rest:
        return root_pc, "major"
    return root_pc, None


def _scale_pitches(scale_intervals: list[int], root_pc: int, lo: int, hi: int) -> list[int]:
    out = []
    for octv in range(-1, 11):
        base = octv * 12
        for iv in scale_intervals:
            p = base + root_pc + iv
            if lo <= p <= hi:
                out.append(p)
    return sorted(set(out))


def _weighted_pick(rng: random.Random, candidates: list[int], center: int) -> int:
    if not candidates:
        return center
    weights = [1.0 / ((abs(p - center) + 1) ** 1.5) for p in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def _fill_bar_rhythm(rng: random.Random, rhythm_choices: list[float], rest_prob: float) -> list[tuple[float, float, bool]]:
    t = 0.0
    slots: list[tuple[float, float, bool]] = []
    while t < BEATS_PER_BAR - 1e-6:
        remaining = BEATS_PER_BAR - t
        options = [d for d in rhythm_choices if d <= remaining + 1e-6] or [remaining]
        dur = rng.choice(options)
        is_rest = rng.random() < rest_prob
        slots.append((t, dur, is_rest))
        t += dur
    return slots


def _generate_melody_bar(rng, preset: GenrePreset, chord: Chord, scale_intervals, root_pc,
                          bar_start: float, prev_pitch: int | None, thin: bool) -> tuple[list[NoteEvent], int]:
    lo = (preset.lead_octave) * 12
    hi = (preset.lead_octave + 2) * 12
    chord_tones = [p for p in chord.midi_pitches(preset.lead_octave) if lo <= p <= hi]
    chord_tones += [p + 12 for p in chord_tones if lo <= p + 12 <= hi]
    scale_tones = _scale_pitches(scale_intervals, root_pc, lo, hi)
    center = prev_pitch if prev_pitch is not None else (chord_tones[0] if chord_tones else (lo + hi) // 2)

    rest_prob = 0.35 if thin else 0.12
    rhythm = [max(d, 1.0) for d in preset.melody_rhythm] if thin else preset.melody_rhythm
    slots = _fill_bar_rhythm(rng, rhythm, rest_prob)

    events: list[NoteEvent] = []
    for t, dur, is_rest in slots:
        if is_rest:
            continue
        on_strong_beat = abs(t - round(t)) < 1e-6
        pool = chord_tones if (on_strong_beat or rng.random() > 0.4) else scale_tones
        pitch = _weighted_pick(rng, pool or scale_tones or chord_tones, center)
        vel = 78 if thin else rng.randint(85, 105)
        start = bar_start + t
        if not on_strong_beat and rng.random() < preset.syncopation:
            start -= 0.08  # subtle push-ahead feel
        events.append(NoteEvent(start=max(bar_start, start), dur=dur * 0.92, pitch=pitch, vel=vel))
        center = pitch
    return events, center


def _generate_bass_bar(rng, preset: GenrePreset, chord: Chord, next_chord: Chord, bar_start: float, thin: bool) -> list[NoteEvent]:
    style = BASS_STYLE_BY_GENRE.get(preset.name, "root_fifth")
    pattern = BASS_STYLES[style]
    base = chord.root_pc + (preset.bass_octave + 1) * 12
    events = []
    for beat_off, tone_ref, dur in pattern:
        if tone_ref == "approach":
            target = next_chord.root_pc + (preset.bass_octave + 1) * 12
            pitch = target - 1
        else:
            idx = min(tone_ref, len(chord.tones) - 1)
            pitch = base + chord.tones[idx]
        vel = 70 if thin else rng.randint(80, 100)
        events.append(NoteEvent(start=bar_start + beat_off, dur=dur * 0.95, pitch=pitch, vel=vel))
    return events


def _generate_chord_bar(preset: GenrePreset, chord: Chord, bar_start: float, thin: bool) -> list[NoteEvent]:
    pitches = chord.midi_pitches(preset.chord_octave)
    vel = 42 if thin else 58
    return [NoteEvent(start=bar_start, dur=BEATS_PER_BAR * 0.98, pitch=p, vel=vel) for p in pitches]


def _generate_drum_bar(rng, preset: GenrePreset, bar_start: float, thin: bool, include_snare: bool) -> list[NoteEvent]:
    dp = preset.drum
    step_dur = BEATS_PER_BAR / 16.0
    events = []
    grids = [("kick", dp.kick, 108), ("hihat", dp.hihat, 68), ("perc", dp.perc, 75)]
    if include_snare:
        grids.insert(1, ("snare", dp.snare, 96))
    for name, grid, base_vel in grids:
        if thin and name in ("snare", "perc"):
            continue
        for i, hit in enumerate(grid):
            if not hit:
                continue
            t = i * step_dur
            if dp.swing and i % 2 == 1:
                t += dp.swing * step_dur
            vel = base_vel + rng.randint(-8, 8)
            events.append(NoteEvent(start=bar_start + t, dur=step_dur * 0.9, vel=max(1, vel), drum=name))
    return events


def build_composition(genre: str, key: str = "C major", tempo: int | None = None,
                       structure: list[str] | None = None, seed: int | None = None,
                       length: str = "full") -> Composition:
    preset = get_preset(genre)
    root_pc, explicit_mode = _parse_key_mode(key)
    scale_name = explicit_mode or preset.scale
    scale_intervals = theory.SCALES[scale_name]

    if tempo is None:
        lo, hi = preset.tempo_range
        tempo = (lo + hi) // 2
    if structure is None:
        structure = SHORT_STRUCTURE if length == "short" else DEFAULT_STRUCTURE

    rng = random.Random(seed)

    # Pre-compute one chord per bar across the whole song.
    bars_info = []  # (section_name, bar_index_in_section, Chord)
    prog_pool = preset.progressions
    for s_idx, name in enumerate(structure):
        bars = SECTION_BARS[name]
        progression = prog_pool[s_idx % len(prog_pool)]
        for i in range(bars):
            degree = progression[i % len(progression)]
            chord = build_chord(scale_intervals, root_pc, degree, seventh=preset.seventh_chords)
            bars_info.append((name, chord))

    sections = []
    bar_cursor = 0
    for name in structure:
        bars = SECTION_BARS[name]
        degrees = [bars_info[bar_cursor + i][1].degree for i in range(bars)]
        sections.append(Section(name=name, start_bar=bar_cursor, bars=bars, chord_degrees=degrees))
        bar_cursor += bars

    comp = Composition(
        genre=preset.name, key=key, tempo=tempo, beats_per_bar=BEATS_PER_BAR,
        total_bars=len(bars_info), sections=sections,
        lead_voice=preset.lead_voice, bass_voice=preset.bass_voice, chord_voice=preset.chord_voice,
    )

    prev_pitch = None
    total = len(bars_info)
    for i, (name, chord) in enumerate(bars_info):
        bar_start = i * BEATS_PER_BAR
        thin = name in ("intro", "outro") and (i < 2 or i >= total - 2)
        include_snare = not (name == "intro" and i < 2)
        next_chord = bars_info[(i + 1) % total][1]

        mel_events, prev_pitch = _generate_melody_bar(rng, preset, chord, scale_intervals, root_pc, bar_start, prev_pitch, thin)
        comp.melody.extend(mel_events)
        comp.bass.extend(_generate_bass_bar(rng, preset, chord, next_chord, bar_start, thin))
        comp.chords_track.extend(_generate_chord_bar(preset, chord, bar_start, thin))
        comp.drums.extend(_generate_drum_bar(rng, preset, bar_start, thin, include_snare))

    return comp
