"""Generates a ready-to-paste prompt pack for cloud vocal-song generators
(Suno, Udio, etc).

Claude Composer's own synth.py always gives you a usable instrumental
with nothing to install. This module is the complementary path for when
you want a fully sung vocal track: it formats style tags + a
section-tagged lyric sheet the way dedicated "Suno songwriting skill"
projects do (researched from public Claude-Code Suno/Udio skills), so
you can paste it straight into Suno or Udio and get vocals back.
"""
from __future__ import annotations

from .arranger import Composition
from .lyrics import LyricSet

STYLE_TAG_HINTS = {
    "lofi": "lo-fi hip hop, dusty vinyl crackle, mellow electric piano, boom-bap drums, chillhop",
    "pop": "modern pop, catchy hook, bright synths, radio-ready production",
    "edm": "progressive house / EDM, four-on-the-floor kick, big room synth lead, festival energy",
    "jazz": "smooth jazz, walking upright bass, brushed drums, warm electric piano",
    "cinematic": "cinematic orchestral, sweeping strings, emotional, film score",
    "acoustic": "acoustic singer-songwriter, fingerstyle guitar, warm and intimate",
}


def build_suno_prompt(comp: Composition, mood: str | None, lyrics: LyricSet | None) -> str:
    style = STYLE_TAG_HINTS.get(comp.genre, comp.genre)
    mood_part = f", {mood} mood" if mood else ""
    lines = [f"[Style] {style}{mood_part}, key of {comp.key}, {comp.tempo} BPM", ""]

    for sec in comp.sections:
        tag = sec.name.capitalize()
        sec_lines = (lyrics.sections.get(sec.name) if lyrics else None) or []
        lines.append(f"[{tag}]")
        if sec_lines:
            lines.extend(sec_lines)
        elif sec.name in ("intro", "outro"):
            lines.append("(instrumental)")
        else:
            lines.append("(가사를 여기에 적어주세요 / write lyrics here)")
        lines.append("")

    lines.append("--- 사용법 ---")
    lines.append("위 텍스트를 Suno(suno.com) 또는 Udio(udio.com)의 커스텀 모드 프롬프트/가사 칸에 그대로 붙여넣으세요.")
    lines.append("[Style] 줄은 스타일/프롬프트 칸에, [Verse]/[Chorus] 이하는 가사 칸에 넣으면 됩니다.")
    return "\n".join(lines).strip() + "\n"
