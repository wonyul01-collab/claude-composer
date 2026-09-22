"""Pure-stdlib Standard MIDI File (format 1) writer.

No third-party dependencies (no mido/midiutil). Produces a .mid file that
opens in any DAW (GarageBand, FL Studio, Ableton, MuseScore, ...).
"""
from __future__ import annotations

import struct

from .arranger import Composition, NoteEvent

PPQ = 480  # ticks per quarter note

# General MIDI program numbers (0-indexed) per synth-voice name used in theory.py
VOICE_PROGRAM = {
    "epiano": 4, "pluck": 24, "pad": 89, "saw": 81, "strings": 48,
    "subbass": 38, "synthbass": 39, "upright": 32,
}

DRUM_NOTE = {"kick": 36, "snare": 38, "hihat": 42, "perc": 39}


def _vlq(value: int) -> bytes:
    """Encode a non-negative int as a MIDI variable-length quantity."""
    buf = [value & 0x7F]
    value >>= 7
    while value:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(buf))


def _chunk(tag: bytes, data: bytes) -> bytes:
    return tag + struct.pack(">I", len(data)) + data


def _meta(kind: int, data: bytes) -> bytes:
    return bytes([0xFF, kind]) + _vlq(len(data)) + data


def _tempo_meta(bpm: float) -> bytes:
    micros = int(round(60_000_000 / bpm))
    return _meta(0x51, struct.pack(">I", micros)[1:])


def _track_name_meta(name: str) -> bytes:
    return _meta(0x03, name.encode("ascii", "ignore"))


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(v))))


def _events_to_track(raw_events: list[tuple[float, int]], channel: int, program: int | None, name: str) -> bytes:
    """raw_events: list of (abs_tick, priority, bytes) already built by caller helpers."""
    body = bytearray()
    if program is not None:
        prog_ev = [(0, -1, _track_name_meta(name)), (0, 0, bytes([0xC0 | channel, program]))]
    else:
        prog_ev = [(0, -1, _track_name_meta(name))]
    all_events = sorted(prog_ev + raw_events, key=lambda e: (e[0], e[1]))
    last_tick = 0
    for tick, _prio, data in all_events:
        delta = max(0, tick - last_tick)
        body += _vlq(delta) + data
        last_tick = tick
    body += _vlq(0) + _meta(0x2F, b"")
    return _chunk(b"MTrk", bytes(body))


def _note_events(events: list[NoteEvent], channel: int) -> list[tuple[int, int, bytes]]:
    out = []
    for ev in events:
        if ev.dur <= 0:
            continue
        start_tick = int(round(ev.start * PPQ))
        end_tick = int(round((ev.start + ev.dur) * PPQ))
        if end_tick <= start_tick:
            end_tick = start_tick + 1
        pitch = _clamp(ev.pitch, 0, 127)
        vel = _clamp(ev.vel, 1, 127)
        out.append((start_tick, 1, bytes([0x90 | channel, pitch, vel])))
        out.append((end_tick, 0, bytes([0x80 | channel, pitch, 0])))
    return out


def _drum_events(events: list[NoteEvent], channel: int = 9) -> list[tuple[int, int, bytes]]:
    out = []
    for ev in events:
        note = DRUM_NOTE.get(ev.drum or "", 39)
        start_tick = int(round(ev.start * PPQ))
        end_tick = int(round((ev.start + max(ev.dur, 0.05)) * PPQ))
        vel = _clamp(ev.vel, 1, 127)
        out.append((start_tick, 1, bytes([0x90 | channel, note, vel])))
        out.append((end_tick, 0, bytes([0x80 | channel, note, 0])))
    return out


def write_midi(comp: Composition, path: str) -> None:
    tempo_track = bytearray()
    tempo_track += _vlq(0) + _track_name_meta("Claude Composer")
    tempo_track += _vlq(0) + _tempo_meta(comp.tempo)
    tempo_track += _vlq(0) + _meta(0x58, bytes([comp.beats_per_bar, 2, 24, 8]))  # time sig num/4
    tempo_track += _vlq(0) + _meta(0x2F, b"")
    tempo_chunk = _chunk(b"MTrk", bytes(tempo_track))

    melody_chunk = _events_to_track(_note_events(comp.melody, 0), 0, VOICE_PROGRAM[comp.lead_voice], "Melody")
    bass_chunk = _events_to_track(_note_events(comp.bass, 1), 1, VOICE_PROGRAM[comp.bass_voice], "Bass")
    chord_chunk = _events_to_track(_note_events(comp.chords_track, 2), 2, VOICE_PROGRAM[comp.chord_voice], "Chords")
    drum_chunk = _events_to_track(_drum_events(comp.drums), 9, None, "Drums")

    tracks = [tempo_chunk, melody_chunk, bass_chunk, chord_chunk, drum_chunk]
    header = _chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), PPQ))

    with open(path, "wb") as f:
        f.write(header)
        for t in tracks:
            f.write(t)
