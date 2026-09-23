# 국가별 시장 가이드

`python3 -m composer markets` 로 아래 내용을 언제든 CLI에서 확인할 수 있다. `--market <코드>` 를 주면
장르를 안 정해도 그 시장에 맞는 추천 장르가 자동 선택되고, `--suno` 로 만든 프롬프트에도
`[Market]` 블록으로 이 가이드가 함께 들어간다.

## 왜 이 목록인가 — 리서치 근거

`머니몬스터TV`의 "AI 일본 플레이리스트" 영상([설명란](https://youtu.be/53lkMdC3QWY) 기준)이 실제로
보여준 방식은: ChatGPT로 일본어 가사 작성 → Suno로 J-POP 곡 생성 → 일본의 "작업용 BGM/귀가길
플레이리스트" 유튜브 니치를 타깃. 이게 실제로 돈이 되는 니치인지 추가로 확인했다:

- ["작사·작곡은 AI가 하고 돈은 제가 벌어요" 신종 '플레이리스트 유튜버'의 세계](https://v.daum.net/v/20251005060200841) — AI 음악 채널 운영자가 Suno로 작업하며 월 수백만 원대 수익을 내는 실제 사례
- 일본 시티팝(80년대 AOR/펑키 베이스/재즈 코드) 리바이벌은 [Night Tempo](https://en.wikipedia.org/wiki/Night_Tempo) 같은 리믹서들이 주도하며 지금도 작업용 플레이리스트로 꾸준히 소비되고 있음

이 두 가지를 근거로, "일본 = 시티팝·로파이 작업용 BGM이 1순위, 보컬이 필요하면 J-POP" 이라는
`markets.py`의 일본 프로필을 잡았다. 한국·미국·글로벌 로파이는 같은 논리(플랫폼에서 실제로 잘 소비되는
장르가 무엇인가)로 채워 넣은 1차 추천값이며, 특정 국가를 더 깊게 공략하고 싶다면
`docs/MARKETS.md`에 새 `MarketProfile`을 추가하고 근거 링크를 함께 적어두면 된다.

## 시장 목록

| 코드 | 국가 | 추천 장르(우선순위) | 가사 언어 |
|---|---|---|---|
| `japan` | 일본 | citypop → lofi → jpop | 일본어 |
| `korea` | 한국 | kpop → lofi → pop | 한국어 |
| `usa` | 미국 | pop → edm → acoustic | 영어 |
| `global_lofi` | 글로벌(작업용 BGM) | lofi → cinematic | 없음(인스트루멘탈) |

## 시장을 더 늘리려면

`composer/markets.py` 의 `MARKET_PROFILES` 딕셔너리에 `MarketProfile` 하나를 더 추가하면 된다.
그 시장에 맞는 장르가 기존 프리셋에 없다면(예: 라틴 레게톤, 인도 볼리우드 등),
`composer/theory.py` 의 `GENRE_PRESETS` 에 새 `GenrePreset` 을 먼저 추가한 뒤 연결한다 — 이번에
`citypop`/`jpop`/`kpop`을 추가한 방식과 동일하다.
