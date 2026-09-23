"""Command-line interface for Claude Composer.

Examples:
    python3 -m composer genres
    python3 -m composer create --genre lofi --mood "rainy night" --key "D minor" --out my_song
    python3 -m composer create --genre pop --lyrics-json lyrics.json --suno --out my_song
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import theory
from .arranger import build_composition
from .lyrics import load_lyrics_json, placeholder_lyrics
from .markets import MARKET_PROFILES, get_market
from .midiwriter import write_midi
from .suno_prompt import build_suno_prompt
from .synth import render as render_wav


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--genre", default=None, choices=sorted(theory.GENRE_PRESETS),
                    help="장르 프리셋 (--market 만 주면 그 시장의 추천 장르를 자동 사용)")
    p.add_argument("--market", default=None, choices=sorted(MARKET_PROFILES),
                    help="타깃 국가/시장 (지정하면 장르 기본값과 Suno 프롬프트에 해당 시장 가이드가 반영됨)")
    p.add_argument("--mood", default=None, help="분위기 설명 (자유 텍스트, Suno 프롬프트에 반영)")
    p.add_argument("--key", default="C major", help='조성, 예: "C major", "A minor" (기본: C major)')
    p.add_argument("--tempo", type=int, default=None, help="BPM (생략 시 장르 기본값)")
    p.add_argument("--length", choices=["short", "full"], default="short",
                    help="short=약 30~50초 인트로/벌스/코러스/아웃트로, full=풀 송 구조 (기본: short)")
    p.add_argument("--seed", type=int, default=None, help="같은 곡을 재생성하려면 시드 고정")
    p.add_argument("--out", default="song", help="출력 파일 기본 이름 (확장자 제외, 기본: song)")
    p.add_argument("--outdir", default="./output", help="출력 폴더 (기본: ./output)")


def _resolve_genre_and_market(args: argparse.Namespace):
    market = get_market(args.market) if args.market else None
    genre = args.genre
    if genre is None:
        if market is None:
            raise SystemExit("--genre 또는 --market 중 하나는 반드시 지정해야 합니다 (markets 명령으로 목록 확인)")
        genre = market.recommended_genres[0]
    return genre, market


def cmd_create(args: argparse.Namespace) -> int:
    genre, market = _resolve_genre_and_market(args)
    comp = build_composition(
        genre=genre, key=args.key, tempo=args.tempo,
        seed=args.seed, length=args.length,
    )
    os.makedirs(args.outdir, exist_ok=True)
    base = os.path.join(args.outdir, args.out)

    wav_path = f"{base}.wav"
    mid_path = f"{base}.mid"
    if args.format in ("wav", "both"):
        render_wav(comp, wav_path)
    if args.format in ("midi", "both"):
        write_midi(comp, mid_path)

    lyrics = None
    if args.lyrics_json:
        with open(args.lyrics_json, encoding="utf-8") as f:
            lyrics = load_lyrics_json(json.load(f))
    elif args.suno:
        lyrics = placeholder_lyrics(comp)

    prompt_path = None
    if args.suno:
        prompt_path = f"{base}.suno.txt"
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(build_suno_prompt(comp, args.mood, lyrics, market=market))

    struct_summary = " → ".join(f"{s.name}({s.bars}마디)" for s in comp.sections)
    print(f"장르: {comp.genre} | 조성: {comp.key} | 템포: {comp.tempo} BPM | 총 {comp.total_bars}마디 "
          f"(~{comp.duration_seconds:.1f}초)")
    if market:
        print(f"타깃 시장: {market.name_ko} | 권장 가사 언어: {market.lyric_language}")
    print(f"구성: {struct_summary}")
    if args.format in ("wav", "both"):
        print(f"오디오 생성 완료: {wav_path}")
    if args.format in ("midi", "both"):
        print(f"MIDI 생성 완료 (DAW에서 편집 가능): {mid_path}")
    if prompt_path:
        print(f"Suno/Udio 프롬프트 생성 완료: {prompt_path}")
    return 0


def cmd_genres(args: argparse.Namespace) -> int:
    for name, preset in sorted(theory.GENRE_PRESETS.items()):
        lo, hi = preset.tempo_range
        print(f"{name:10s}  {lo}-{hi} BPM  scale={preset.scale}  lead={preset.lead_voice}")
    return 0


def cmd_markets(args: argparse.Namespace) -> int:
    for code, m in sorted(MARKET_PROFILES.items()):
        print(f"[{code}] {m.name_ko} | 추천 장르: {', '.join(m.recommended_genres)} | 가사 언어: {m.lyric_language}")
        print(f"  {m.notes}")
    return 0


def cmd_suno_prompt(args: argparse.Namespace) -> int:
    genre, market = _resolve_genre_and_market(args)
    comp = build_composition(genre=genre, key=args.key, tempo=args.tempo, seed=args.seed, length=args.length)
    lyrics = None
    if args.lyrics_json:
        with open(args.lyrics_json, encoding="utf-8") as f:
            lyrics = load_lyrics_json(json.load(f))
    else:
        lyrics = placeholder_lyrics(comp)
    text = build_suno_prompt(comp, args.mood, lyrics, market=market)
    if args.out_file:
        with open(args.out_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"저장 완료: {args.out_file}")
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="composer", description="Claude Composer - 텍스트 설명으로 음악 만들기")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="곡 생성 (WAV/MIDI)")
    _add_common_args(p_create)
    p_create.add_argument("--format", choices=["wav", "midi", "both"], default="both", help="출력 형식 (기본: both)")
    p_create.add_argument("--lyrics-json", default=None, help='가사 JSON 파일 경로, 예: {"verse":["line1"],"chorus":[...]}')
    p_create.add_argument("--suno", action="store_true", help="Suno/Udio용 프롬프트팩(.suno.txt)도 함께 생성")
    p_create.set_defaults(func=cmd_create)

    p_genres = sub.add_parser("genres", help="사용 가능한 장르 프리셋 목록")
    p_genres.set_defaults(func=cmd_genres)

    p_markets = sub.add_parser("markets", help="국가별 타깃 시장 목록과 추천 장르/가사 언어")
    p_markets.set_defaults(func=cmd_markets)

    p_suno = sub.add_parser("suno-prompt", help="Suno/Udio 프롬프트팩만 생성")
    _add_common_args(p_suno)
    p_suno.add_argument("--lyrics-json", default=None)
    p_suno.add_argument("--out-file", default=None, help="지정하지 않으면 표준출력으로 인쇄")
    p_suno.set_defaults(func=cmd_suno_prompt)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
