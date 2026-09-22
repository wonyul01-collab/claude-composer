"""Pure-stdlib software synthesizer: renders a Composition directly to a
.wav file. No numpy, no FluidSynth, no external SoundFont -- this is what
lets Claude Composer produce actual audio on any machine that has Python,
with nothing to install.
"""
from __future__ import annotations

import math
import random
import wave
from array import array

from .arranger import Composition, NoteEvent

SAMPLE_RATE = 44100
TWO_PI = 2 * math.pi

VOICE_GAIN = {
    "epiano": 0.55, "pluck": 0.5, "pad": 0.35, "saw": 0.4,
    "strings": 0.4, "subbass": 0.7, "synthbass": 0.6, "upright": 0.6,
}
DRUM_GAIN = {"kick": 0.9, "snare": 0.65, "hihat": 0.35, "perc": 0.45}

_rng = random.Random(1234)


def midi_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _adsr(n: int, attack: int, decay: int, sustain_level: float, release: int) -> list[float]:
    env = [0.0] * n
    a = min(attack, n)
    for i in range(a):
        env[i] = i / a if a else 1.0
    d_end = min(a + decay, n)
    for i in range(a, d_end):
        t = (i - a) / decay if decay else 1.0
        env[i] = 1.0 - (1.0 - sustain_level) * t
    r_start = max(d_end, n - release)
    for i in range(d_end, r_start):
        env[i] = sustain_level
    for i in range(r_start, n):
        t = (i - r_start) / max(1, n - r_start)
        env[i] = sustain_level * (1.0 - t)
    return env


def _harmonic_tone(freq: float, n: int, partials: list[tuple[float, float]]) -> list[float]:
    """partials: list of (harmonic_multiple, amplitude)."""
    out = [0.0] * n
    for mult, amp in partials:
        w = TWO_PI * freq * mult / SAMPLE_RATE
        for i in range(n):
            out[i] += amp * math.sin(w * i)
    return out


def _noise(n: int, highpass: bool = False) -> list[float]:
    raw = [_rng.uniform(-1.0, 1.0) for _ in range(n)]
    if not highpass:
        return raw
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        out[i] = raw[i] - prev
        prev = raw[i]
    return out


def _render_pitched(voice: str, freq: float, dur_s: float, velocity: int) -> list[float]:
    n = max(1, int(dur_s * SAMPLE_RATE))
    if voice == "epiano":
        tone = _harmonic_tone(freq, n, [(1, 1.0), (2, 0.28), (4, 0.10)])
        env = _adsr(n, int(0.005 * SAMPLE_RATE), int(0.25 * n), 0.35, int(0.35 * n))
    elif voice == "pluck":
        tone = _harmonic_tone(freq, n, [(1, 1.0), (3, 0.22), (5, 0.08)])
        env = _adsr(n, int(0.003 * SAMPLE_RATE), int(0.15 * n), 0.15, int(0.55 * n))
    elif voice == "pad":
        detune = freq * 0.006
        tone = _harmonic_tone(freq, n, [(1, 0.6), (2, 0.15)])
        tone2 = _harmonic_tone(freq + detune, n, [(1, 0.5)])
        tone3 = _harmonic_tone(freq - detune, n, [(1, 0.5)])
        tone = [a + b + c for a, b, c in zip(tone, tone2, tone3)]
        env = _adsr(n, int(0.25 * n), int(0.1 * n), 0.8, int(0.4 * n))
    elif voice == "strings":
        vib = [1.0 + 0.006 * math.sin(TWO_PI * 5.0 * i / SAMPLE_RATE) for i in range(n)]
        w = TWO_PI * freq / SAMPLE_RATE
        tone = [math.sin(w * i * vib[i]) * 0.7 + math.sin(2 * w * i * vib[i]) * 0.15 for i in range(n)]
        env = _adsr(n, int(0.18 * n), int(0.1 * n), 0.85, int(0.35 * n))
    elif voice == "saw":
        harmonics = [(k, 1.0 / k) for k in range(1, 9)]
        tone = _harmonic_tone(freq, n, harmonics)
        peak = max(1e-6, max(abs(x) for x in tone))
        tone = [x / peak for x in tone]
        env = _adsr(n, int(0.01 * SAMPLE_RATE), int(0.15 * n), 0.7, int(0.25 * n))
    elif voice == "synthbass":
        harmonics = [(1, 1.0), (2, 0.5), (3, 0.25)]
        tone = _harmonic_tone(freq, n, harmonics)
        peak = max(1e-6, max(abs(x) for x in tone))
        tone = [x / peak for x in tone]
        env = _adsr(n, int(0.005 * SAMPLE_RATE), int(0.2 * n), 0.75, int(0.2 * n))
    elif voice == "upright":
        tone = _harmonic_tone(freq, n, [(1, 1.0), (2, 0.18)])
        env = _adsr(n, int(0.005 * SAMPLE_RATE), int(0.2 * n), 0.4, int(0.4 * n))
    else:  # subbass / fallback
        tone = _harmonic_tone(freq, n, [(1, 1.0), (2, 0.12)])
        env = _adsr(n, int(0.008 * SAMPLE_RATE), int(0.15 * n), 0.85, int(0.2 * n))

    gain = VOICE_GAIN.get(voice, 0.5) * (velocity / 127.0)
    return [t * e * gain for t, e in zip(tone, env)]


def _render_drum(name: str, dur_s: float, velocity: int) -> list[float]:
    n = max(1, int(dur_s * SAMPLE_RATE))
    if name == "kick":
        n = max(n, int(0.16 * SAMPLE_RATE))
        out = [0.0] * n
        f0, f1 = 150.0, 42.0
        phase = 0.0
        for i in range(n):
            t = i / SAMPLE_RATE
            freq = f1 + (f0 - f1) * math.exp(-t * 28)
            phase += TWO_PI * freq / SAMPLE_RATE
            env = math.exp(-t * 18)
            click = (1.0 - min(1.0, t / 0.004)) * _rng.uniform(-0.4, 0.4)
            out[i] = (math.sin(phase) * env + click) 
        peak = max(abs(x) for x in out) or 1.0
        out = [x / peak for x in out]
    elif name == "snare":
        noise = _noise(n, highpass=True)
        w = TWO_PI * 190.0 / SAMPLE_RATE
        tone = [math.sin(w * i) for i in range(n)]
        env = _adsr(n, int(0.002 * SAMPLE_RATE), int(0.35 * n), 0.05, int(0.6 * n))
        out = [(0.75 * nz + 0.35 * tn) * e for nz, tn, e in zip(noise, tone, env)]
    elif name == "hihat":
        noise = _noise(n, highpass=True)
        env = _adsr(n, int(0.001 * SAMPLE_RATE), int(0.3 * n), 0.0, int(0.4 * n))
        out = [nz * e for nz, e in zip(noise, env)]
    else:  # perc / clap
        out = [0.0] * n
        burst_starts = [0, int(0.02 * SAMPLE_RATE), int(0.045 * SAMPLE_RATE)]
        for bstart in burst_starts:
            blen = min(int(0.04 * SAMPLE_RATE), n - bstart)
            if blen <= 0:
                continue
            noise = _noise(blen, highpass=True)
            env = _adsr(blen, int(0.001 * SAMPLE_RATE), int(0.5 * blen), 0.0, int(0.3 * blen))
            for i in range(blen):
                out[bstart + i] += noise[i] * env[i]
        peak = max((abs(x) for x in out), default=1.0) or 1.0
        out = [x / peak for x in out]

    gain = DRUM_GAIN.get(name, 0.5) * (0.5 + 0.5 * velocity / 127.0)
    return [x * gain for x in out]


def _mix_in(master: array, offset: int, samples: list[float]) -> None:
    n = len(master)
    for i, s in enumerate(samples):
        idx = offset + i
        if 0 <= idx < n:
            master[idx] += s


def render(comp: Composition, path: str, sample_rate: int = SAMPLE_RATE) -> None:
    beat_to_sample = 60.0 / comp.tempo * sample_rate
    total_samples = int(comp.duration_seconds * sample_rate) + sample_rate  # 1s tail
    master = array("f", bytes(total_samples * 4))

    voices: list[tuple[list[NoteEvent], str]] = [
        (comp.chords_track, comp.chord_voice),
        (comp.bass, comp.bass_voice),
        (comp.melody, comp.lead_voice),
    ]
    for events, voice in voices:
        for ev in events:
            offset = int(ev.start * beat_to_sample)
            freq = midi_to_freq(ev.pitch)
            dur_s = (ev.dur * beat_to_sample) / sample_rate
            samples = _render_pitched(voice, freq, dur_s, ev.vel)
            _mix_in(master, offset, samples)

    for ev in comp.drums:
        offset = int(ev.start * beat_to_sample)
        dur_s = max(ev.dur, 0.05) * beat_to_sample / sample_rate
        samples = _render_drum(ev.drum or "perc", dur_s, ev.vel)
        _mix_in(master, offset, samples)

    # fade the last 0.8s of the tail so it doesn't cut off abruptly
    fade_len = min(total_samples, int(0.8 * sample_rate))
    for i in range(fade_len):
        idx = total_samples - fade_len + i
        master[idx] *= 1.0 - (i / fade_len)

    peak = max((abs(x) for x in master), default=0.0)
    scale = (0.9 / peak) if peak > 0.9 else 1.0

    pcm = array("h", bytes(total_samples * 2))
    for i in range(total_samples):
        v = master[i] * scale
        if v > 1.0:
            v = 1.0
        elif v < -1.0:
            v = -1.0
        pcm[i] = int(v * 32767)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
