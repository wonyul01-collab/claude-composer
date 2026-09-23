"""Country/market profiles.

Each profile gives a short, opinionated answer to "what genre/mood fits
this market's audience?" so the composer can default sensibly and the
Suno/Udio prompt pack can be steered toward the right language and style
descriptors for that market. Grounded in the real "AI playlist channel"
niche (13-year songwriters using ChatGPT + Suno to target Japan's
work-BGM/J-POP audience; see docs/MARKETS.md for sources) rather than
guessed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketProfile:
    code: str
    name_ko: str
    recommended_genres: list[str]   # ordered, most-recommended first
    lyric_language: str              # language Claude should write lyrics in
    notes: str                        # short market-research guide (Korean)


MARKET_PROFILES: dict[str, MarketProfile] = {
    "japan": MarketProfile(
        code="japan", name_ko="일본",
        recommended_genres=["citypop", "lofi", "jpop"],
        lyric_language="일본어",
        notes=(
            "일본 유튜브는 '작업용 BGM'/'귀가길 플레이리스트' 같은 무보컬~가벼운 "
            "보컬의 롱폼 플레이리스트 채널이 강세다. 80년대 시티팝 리바이벌(신스 "
            "+펑키 베이스+재즈 코드)과 로파이 힙합이 특히 잘 먹히고, 보컬곡을 "
            "원하면 밝고 빠른 코드 진행의 J-POP/애니송 스타일이 강세다. Suno에 "
            "가사를 넣을 때는 일본어로 쓰고, 영어 병기를 병행하면 제작자 본인이 "
            "이해하기 쉽다."
        ),
    ),
    "korea": MarketProfile(
        code="korea", name_ko="한국",
        recommended_genres=["kpop", "lofi", "pop"],
        lyric_language="한국어",
        notes=(
            "국내는 K-POP 특유의 트랩/EDM 영향을 받은 훅 중심 구성이 강세이고, "
            "공부·작업용 콘텐츠로는 로파이·시티팝도 꾸준히 소비된다. 가사는 "
            "한국어 후렴 반복 + 영어 훅 혼용이 흔하다."
        ),
    ),
    "usa": MarketProfile(
        code="usa", name_ko="미국", recommended_genres=["pop", "edm", "acoustic"],
        lyric_language="영어",
        notes=(
            "미국은 장르 스펙트럼이 넓지만, 스트리밍 플레이리스트향으로는 밝은 "
            "팝, 빅룸/프로그레시브 EDM, 어쿠스틱 싱어송라이터 톤이 꾸준히 "
            "수요가 있다."
        ),
    ),
    "global_lofi": MarketProfile(
        code="global_lofi", name_ko="글로벌 (작업용 BGM)",
        recommended_genres=["lofi", "cinematic"],
        lyric_language="없음 (인스트루멘탈)",
        notes=(
            "국가를 가리지 않는 가장 안전한 니치는 무보컬 로파이/시네마틱 "
            "작업용 BGM이다. 언어 장벽이 없어 전 세계 어디서나 소비되고, 저작권 "
            "분쟁 위험도 가장 낮다."
        ),
    ),
}


def get_market(market: str) -> MarketProfile:
    key = market.strip().lower()
    if key not in MARKET_PROFILES:
        raise ValueError(f"Unknown market {market!r}. Available: {', '.join(sorted(MARKET_PROFILES))}")
    return MARKET_PROFILES[key]
