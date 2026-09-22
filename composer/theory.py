"""Music theory primitives: notes, scales, chords, and genre presets.

No external dependencies. Pitches are represented as MIDI note numbers
(0-127, 60 = middle C).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

NOTE_INDEX = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "FB": 4,
    "F": 5, "E#": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9,
    "A#": 10, "BB": 10, "B": 11, "CB": 11,
}

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
}

# Scale-degree triads/7ths as semitone offsets from the chord root, keyed by
# how a chord built on that scale degree normally functions in the given mode.
TRIAD = [0, 4, 7]
SEVENTH_MAJ7 = [0, 4, 7, 11]
SEVENTH_MIN7 = [0, 3, 7, 10]
SEVENTH_DOM7 = [0, 4, 7, 10]
SEVENTH_HALFDIM = [0, 3, 6, 10]


def parse_note(name: str) -> int:
    """Parse a note name like 'C4', 'F#3', 'Bb5' into a MIDI note number."""
    m = re.match(r"^([A-Ga-g])([#bB]?)(-?\d+)$", name.strip())
    if not m:
        raise ValueError(f"Invalid note name: {name!r}")
    letter, accidental, octave = m.groups()
    key = (letter.upper() + accidental.upper()).replace("B", "b").upper()
    # normalize: letter uppercase, accidental as '#' or 'B'
    key = letter.upper() + (accidental.upper() if accidental else "")
    if key not in NOTE_INDEX:
        raise ValueError(f"Invalid note name: {name!r}")
    return NOTE_INDEX[key] + (int(octave) + 1) * 12


def parse_key(key: str) -> tuple[int, str]:
    """Parse a key spec like 'C major' or 'A minor' -> (root_pc, mode)."""
    parts = key.strip().split()
    root = parts[0].upper()
    mode = "natural_minor" if len(parts) > 1 and parts[1].lower().startswith("min") else "major"
    if root not in NOTE_INDEX:
        raise ValueError(f"Unknown key root: {key!r}")
    return NOTE_INDEX[root], mode


@dataclass
class Chord:
    root_pc: int          # pitch class 0-11
    tones: list[int]       # semitone offsets from root (chord shape)
    degree: int             # scale degree 1-7 (for readability/debug)

    def midi_pitches(self, octave: int = 4) -> list[int]:
        base = self.root_pc + (octave + 1) * 12
        return [base + t for t in self.tones]


def build_chord(scale: list[int], root_pc_of_scale: int, degree: int, seventh: bool = True) -> Chord:
    """Build a chord on the given 1-indexed scale degree."""
    n = len(scale)
    idx = degree - 1
    root_offset = scale[idx % n]
    third = scale[(idx + 2) % n] + (12 if (idx + 2) >= n else 0)
    fifth = scale[(idx + 4) % n] + (12 if (idx + 4) >= n else 0)
    tones = [0, third - root_offset, fifth - root_offset]
    if seventh:
        seventh_off = scale[(idx + 6) % n] + (12 if (idx + 6) >= n else 0)
        tones.append(seventh_off - root_offset)
    root_pc = (root_pc_of_scale + root_offset) % 12
    return Chord(root_pc=root_pc, tones=tones, degree=degree)


# ---------------------------------------------------------------------------
# Genre presets
# ---------------------------------------------------------------------------

@dataclass
class DrumPattern:
    """16-step grid per genre; 1 = hit, 0 = rest. One bar = 16 sixteenth notes."""
    kick: list[int]
    snare: list[int]
    hihat: list[int]
    perc: list[int] = field(default_factory=lambda: [0] * 16)
    swing: float = 0.0  # 0..0.33, delay applied to off-beat 16ths


@dataclass
class GenrePreset:
    name: str
    tempo_range: tuple[int, int]
    default_mode: str
    scale: str
    progressions: list[list[int]]   # pools of scale-degree progressions (7th chords)
    seventh_chords: bool
    drum: DrumPattern
    melody_rhythm: list[float]       # candidate note durations in beats
    lead_octave: int
    bass_octave: int
    chord_octave: int
    lead_voice: str                  # synth voice name, see synth.py
    bass_voice: str
    chord_voice: str
    swing: float = 0.0
    syncopation: float = 0.35        # probability a melody note starts off-grid


GENRE_PRESETS: dict[str, GenrePreset] = {
    "lofi": GenrePreset(
        name="lofi", tempo_range=(70, 85), default_mode="major", scale="major",
        progressions=[[1, 6, 2, 5], [2, 5, 1, 6], [1, 4, 2, 5]],
        seventh_chords=True,
        drum=DrumPattern(
            kick=[1,0,0,0, 0,0,1,0, 0,0,0,1, 0,0,0,0],
            snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            hihat=[1,0,1,1, 0,1,1,0, 1,0,1,1, 0,1,1,0],
            swing=0.18,
        ),
        melody_rhythm=[0.5, 0.75, 1.0, 1.5],
        lead_octave=5, bass_octave=2, chord_octave=3,
        lead_voice="epiano", bass_voice="subbass", chord_voice="epiano",
        swing=0.18, syncopation=0.5,
    ),
    "pop": GenrePreset(
        name="pop", tempo_range=(100, 120), default_mode="major", scale="major",
        progressions=[[1, 5, 6, 4], [6, 4, 1, 5], [1, 6, 4, 5]],
        seventh_chords=False,
        drum=DrumPattern(
            kick=[1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,1,0],
            snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            hihat=[1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        ),
        melody_rhythm=[0.5, 0.5, 1.0],
        lead_octave=5, bass_octave=2, chord_octave=4,
        lead_voice="pluck", bass_voice="synthbass", chord_voice="pad",
        syncopation=0.25,
    ),
    "edm": GenrePreset(
        name="edm", tempo_range=(124, 130), default_mode="natural_minor", scale="natural_minor",
        progressions=[[1, 7, 6, 7], [1, 6, 3, 7], [6, 7, 1, 1]],
        seventh_chords=False,
        drum=DrumPattern(
            kick=[1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            hihat=[0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
            perc=[0,0,0,1, 0,0,0,1, 0,0,0,1, 0,0,0,1],
        ),
        melody_rhythm=[0.25, 0.5, 0.5],
        lead_octave=5, bass_octave=2, chord_octave=4,
        lead_voice="saw", bass_voice="synthbass", chord_voice="saw",
        syncopation=0.2,
    ),
    "jazz": GenrePreset(
        name="jazz", tempo_range=(90, 116), default_mode="major", scale="major",
        progressions=[[2, 5, 1, 1], [1, 6, 2, 5], [3, 6, 2, 5]],
        seventh_chords=True,
        drum=DrumPattern(
            kick=[1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
            snare=[0,0,0,0, 1,0,0,1, 0,0,0,0, 1,0,0,0],
            hihat=[1,0,1,1, 1,0,1,1, 1,0,1,1, 1,0,1,1],
            swing=0.25,
        ),
        melody_rhythm=[0.33, 0.5, 0.75, 1.0],
        lead_octave=5, bass_octave=3, chord_octave=4,
        lead_voice="epiano", bass_voice="upright", chord_voice="epiano",
        swing=0.25, syncopation=0.55,
    ),
    "cinematic": GenrePreset(
        name="cinematic", tempo_range=(60, 80), default_mode="natural_minor", scale="natural_minor",
        progressions=[[1, 6, 4, 5], [1, 4, 6, 5], [6, 4, 1, 5]],
        seventh_chords=False,
        drum=DrumPattern(
            kick=[1,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
            snare=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
            hihat=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
        ),
        melody_rhythm=[1.0, 1.5, 2.0],
        lead_octave=5, bass_octave=2, chord_octave=3,
        lead_voice="strings", bass_voice="subbass", chord_voice="strings",
        syncopation=0.1,
    ),
    "acoustic": GenrePreset(
        name="acoustic", tempo_range=(85, 105), default_mode="major", scale="major",
        progressions=[[1, 5, 6, 4], [1, 4, 5, 5], [6, 5, 4, 5]],
        seventh_chords=False,
        drum=DrumPattern(
            kick=[1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
            snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            hihat=[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        ),
        melody_rhythm=[0.5, 1.0, 1.0],
        lead_octave=5, bass_octave=3, chord_octave=4,
        lead_voice="pluck", bass_voice="upright", chord_voice="pluck",
        syncopation=0.2,
    ),
}


def get_preset(genre: str) -> GenrePreset:
    key = genre.strip().lower()
    if key not in GENRE_PRESETS:
        raise ValueError(f"Unknown genre {genre!r}. Available: {', '.join(sorted(GENRE_PRESETS))}")
    return GENRE_PRESETS[key]
