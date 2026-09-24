import os
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from composer import theory
from composer.arranger import build_composition
from composer.lyrics import load_lyrics_json, placeholder_lyrics, syllable_budget
from composer.markets import MARKET_PROFILES, get_market
from composer.midiwriter import write_midi
from composer.suno_prompt import build_suno_prompt
from composer.synth import render as render_wav


class TheoryTests(unittest.TestCase):
    def test_parse_note(self):
        self.assertEqual(theory.parse_note("C4"), 60)
        self.assertEqual(theory.parse_note("A4"), 69)
        self.assertEqual(theory.parse_note("C#4"), 61)

    def test_build_chord_triad(self):
        chord = theory.build_chord(theory.SCALES["major"], 0, 1, seventh=False)
        self.assertEqual(sorted(chord.tones), [0, 4, 7])  # C major I

    def test_all_genre_presets_have_valid_progressions(self):
        for name, preset in theory.GENRE_PRESETS.items():
            for prog in preset.progressions:
                for degree in prog:
                    self.assertTrue(1 <= degree <= 7, f"{name}: bad degree {degree}")


class ArrangerTests(unittest.TestCase):
    def test_build_composition_short(self):
        comp = build_composition(genre="pop", key="C major", seed=1, length="short")
        self.assertEqual(comp.total_bars, 24)  # intro4+verse8+chorus8+outro4
        self.assertGreater(len(comp.melody), 0)
        self.assertGreater(len(comp.bass), 0)
        self.assertGreater(len(comp.drums), 0)
        for ev in comp.melody:
            self.assertTrue(0 <= ev.pitch <= 127)

    def test_deterministic_with_seed(self):
        a = build_composition(genre="lofi", key="D minor", seed=42, length="short")
        b = build_composition(genre="lofi", key="D minor", seed=42, length="short")
        self.assertEqual([e.pitch for e in a.melody], [e.pitch for e in b.melody])

    def test_all_genres_generate(self):
        for name in theory.GENRE_PRESETS:
            comp = build_composition(genre=name, seed=3, length="short")
            self.assertGreater(comp.total_bars, 0)


class MidiWriterTests(unittest.TestCase):
    def test_writes_valid_header(self):
        comp = build_composition(genre="pop", seed=5, length="short")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.mid")
            write_midi(comp, path)
            with open(path, "rb") as f:
                data = f.read()
            self.assertEqual(data[:4], b"MThd")
            self.assertGreater(len(data), 100)


class SynthTests(unittest.TestCase):
    def test_renders_short_audio(self):
        # tiny composition: a single 4-bar intro section only, to keep the test fast
        comp = build_composition(genre="edm", seed=9, structure=["intro"])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.wav")
            render_wav(comp, path)
            with wave.open(path, "rb") as w:
                self.assertEqual(w.getframerate(), 44100)
                self.assertGreater(w.getnframes(), 1000)


class LyricsSunoTests(unittest.TestCase):
    def test_placeholder_and_prompt(self):
        comp = build_composition(genre="lofi", seed=2, length="short")
        lyrics = placeholder_lyrics(comp)
        prompt = build_suno_prompt(comp, "chill", lyrics)
        self.assertIn("[Style]", prompt)
        self.assertIn("[Chorus]", prompt)

    def test_load_lyrics_json(self):
        ls = load_lyrics_json({"verse": ["a", "b"]})
        self.assertEqual(ls.sections["verse"], ["a", "b"])

    def test_syllable_budget_matches_sections(self):
        comp = build_composition(genre="pop", seed=4, length="short")
        budget = syllable_budget(comp)
        section_names = {s.name for s in comp.sections}
        self.assertTrue(set(budget.keys()).issubset(section_names))


class MarketExpansionTests(unittest.TestCase):
    def test_new_genre_presets_generate(self):
        for name in ("citypop", "jpop", "kpop"):
            comp = build_composition(genre=name, seed=1, length="short")
            self.assertGreater(comp.total_bars, 0)
            self.assertGreater(len(comp.melody), 0)
            self.assertGreater(len(comp.bass), 0)

    def test_all_markets_have_valid_recommended_genres(self):
        for code, m in MARKET_PROFILES.items():
            self.assertGreater(len(m.recommended_genres), 0)
            for g in m.recommended_genres:
                self.assertIn(g, theory.GENRE_PRESETS, f"{code}: unknown genre {g!r}")

    def test_get_market_unknown_raises(self):
        with self.assertRaises(ValueError):
            get_market("atlantis")

    def test_suno_prompt_includes_market_block(self):
        comp = build_composition(genre="citypop", seed=1, length="short")
        market = get_market("japan")
        prompt = build_suno_prompt(comp, None, placeholder_lyrics(comp), market=market)
        self.assertIn("[Market]", prompt)
        self.assertIn("일본어", prompt)


class ApiTests(unittest.TestCase):
    def test_compose_writes_files_and_is_reproducible(self):
        from composer.api import compose
        with tempfile.TemporaryDirectory() as d:
            a = compose("lofi", os.path.join(d, "a"), key="D minor", seed=5, length="short")
            b = compose("lofi", os.path.join(d, "b"), key="D minor", seed=5, length="short")
            self.assertTrue(os.path.getsize(a["wav"]) > 1000)
            self.assertTrue(os.path.exists(a["mid"]))
            self.assertEqual(a["seed"], 5)
            with open(a["mid"], "rb") as fa, open(b["mid"], "rb") as fb:
                self.assertEqual(fa.read(), fb.read())


if __name__ == "__main__":
    unittest.main()
