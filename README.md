# Claude Composer

자연어 설명 한 줄로 Claude(Code)가 실제로 들을 수 있는 음악을 만들어주는
프로그램. **설치할 게 없다** — 파이썬 표준 라이브러리만으로 작곡부터 오디오
합성까지 다 처리한다 (외부 패키지·GPU·SoundFont·FluidSynth 불필요).

> 어떻게 설계됐는지, 어떤 프로젝트들을 참고했는지는 [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) 참고.

## 무엇을 만들어주나

한 번의 명령으로 아래 세 가지를 받는다.

1. **`.wav` 오디오** — 코드/멜로디/베이스/드럼을 파이썬으로 직접 합성한, 바로 재생 가능한 곡
2. **`.mid` MIDI 파일** — 개러지밴드, FL Studio, Ableton, MuseScore 등 아무 DAW에서나 열어서 악기를 바꾸거나 편집 가능
3. **(선택) Suno/Udio 프롬프트팩** — 사람 목소리로 부르는 완성곡이 필요하면, 이 텍스트를 [Suno](https://suno.com)나 [Udio](https://udio.com)에 그대로 붙여넣으면 됨

## 빠른 시작

파이썬 3.9 이상만 있으면 된다 (Mac/Windows/Linux 어디든 기본 내장).

```
python3 -m composer create --genre lofi --mood "비 오는 밤" --key "D minor" --out my_song
```

실행하면 `./output/my_song.wav` 와 `./output/my_song.mid` 가 생긴다.

### 사용 가능한 장르 확인

```
python3 -m composer genres
```

| 장르 | 분위기 |
|---|---|
| `lofi` | 잔잔한 로파이 힙합, 재즈 코드 + 부드러운 드럼 |
| `pop` | 신나는 팝, 밝은 훅 |
| `edm` | 4비트 킥의 댄스/EDM |
| `jazz` | 스윙, 워킹 베이스, 텐션 코드 |
| `cinematic` | 오케스트라풍 배경음악 |
| `acoustic` | 어쿠스틱 기타 감성 |
| `citypop` | 일본 80년대 시티팝 (펑키 베이스 + 재즈 코드 + 반짝이는 신스) |
| `jpop` | 밝고 빠른 J-POP/애니송 스타일 |
| `kpop` | EDM/트랩 영향의 K-POP 훅 사운드 |

### 해외 음악 시장 타깃 (일본/한국/미국 등)

장르를 직접 고르지 않고 국가만 정해도 된다 — 그 나라에서 잘 먹히는 장르를 자동으로 골라준다.

```
python3 -m composer markets   # 지원하는 시장과 추천 장르/가사 언어 목록
python3 -m composer create --market japan --mood "노을 지는 퇴근길" --suno --out my_song
```

`--market japan` 을 주면 자동으로 `citypop` 장르가 선택되고, `--suno` 로 만든 프롬프트에는
"이 시장에서는 왜 이 장르가 맞는지"를 설명하는 `[Market]` 가이드 블록과 권장 가사 언어(일본어)가
함께 들어간다. 각 시장의 추천 근거는 [`docs/MARKETS.md`](docs/MARKETS.md) 에 정리해뒀다.

### 자주 쓰는 옵션

```
python3 -m composer create \
  --genre pop --mood "신나는" --key "C major" --tempo 118 \
  --length short   # short(약 30~50초, 기본) 또는 full(2분 이상 풀 송 구조) \
  --seed 42         # 같은 곡을 다시 만들고 싶을 때 (숫자만 바꾸면 다른 버전) \
  --out my_song --outdir ./output
```

### 가사가 있는 곡 / Suno·Udio용 보컬 트랙 만들기

이 프로그램은 악기 소리만 합성한다 (사람 목소리는 만들지 못함). 보컬이
있는 완성곡을 원하면, 가사를 JSON으로 준비해서 `--suno` 옵션을 추가한다.

`lyrics.json`:
```json
{
  "verse": ["창밖에 비가 내리는 밤", "너의 목소리가 그리워"],
  "chorus": ["이 노래를 너에게 보낼게", "잊지 말아줘 우리의 밤을"]
}
```

```
python3 -m composer create --genre lofi --key "D minor" \
  --lyrics-json lyrics.json --suno --out my_song
```

`./output/my_song.suno.txt` 가 생성된다. 이 파일의 `[Style]` 줄은
Suno/Udio의 스타일 칸에, `[Verse]`/`[Chorus]` 이하는 가사 칸에 붙여넣으면
된다. Claude Code 안에서 이 프로그램을 스킬로 쓰면(아래 참고), Claude가
직접 가사를 써서 이 파일을 만들어준다.

## Claude Code 안에서 대화로 쓰기 (권장)

이 저장소를 클론해서 Claude Code로 열면, `.claude/skills/composer/SKILL.md`
가 자동으로 인식된다. 그냥 채팅창에 이렇게 치면 된다.

> "비 오는 밤 느낌의 로파이 비트 하나 만들어줘. 가사도 붙여서 Suno에 쓸 수 있게."

Claude가 장르/분위기/조성을 해석하고, 필요하면 직접 가사를 써서 위 CLI를
대신 실행해준다.

## 프로젝트 구조

```
composer/
  theory.py       음계, 코드, 장르 프리셋 (템포·코드진행·드럼 패턴·악기)
  arranger.py     장르 프리셋으로 코드진행+멜로디+베이스+드럼을 생성 (마르코프식 가중 랜덤워크)
  midiwriter.py   표준 MIDI 파일(.mid)을 외부 라이브러리 없이 직접 작성
  synth.py        WAV 오디오를 외부 라이브러리 없이 직접 합성 (신스보이스 8종 + 드럼 4종)
  lyrics.py       가사 템플릿 / 섹션별 음절 수(멜로디 음표 수) 힌트
  markets.py      국가별 타깃 시장 프로필 (추천 장르, 가사 언어, 시장 가이드)
  suno_prompt.py  Suno/Udio용 프롬프트팩 생성
  cli.py          명령줄 인터페이스 (create / genres / suno-prompt)
tests/            unittest 기반 회귀 테스트
docs/BENCHMARKS.md  리서치한 벤치마킹 대상과 설계 근거
.claude/skills/composer/SKILL.md   Claude Code 스킬 정의
```

## 테스트

```
python3 -m unittest discover -s tests -v
```

## 다음 업그레이드 후보

- GPU가 있는 사용자를 위한 로컬 diffusion 모델(예: ACE-Step) 선택적 연동
- 웹 대시보드(브라우저에서 파형 미리듣기 + 장르 선택 UI)
- 곡 일부만 다시 생성하는 "섹션 리페인트" 기능
- 스테레오 합성 + 리버브 등 이펙트 체인

자세한 배경은 [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) 참고.

## 라이선스

MIT — 자유롭게 쓰고 고치고 공유해도 됩니다.
