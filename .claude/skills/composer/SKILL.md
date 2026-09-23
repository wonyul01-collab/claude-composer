---
name: composer
description: Claude를 이용해 자연어 설명만으로 음악(오디오 WAV + MIDI + 가사/Suno 프롬프트)을 만든다. "음악 만들어줘", "노래 만들어줘", "OO 느낌 곡 하나", "로파이 비트", "BGM 만들어줘" 같은 요청에서 사용.
---

# Claude Composer

사용자가 자연어로 곡을 요청하면, 이 스킬은 저장소 안의 순수 파이썬 엔진
(`composer` 패키지, 외부 설치 불필요)을 호출해 실제로 들을 수 있는 WAV
오디오와 DAW에서 열리는 MIDI 파일을 즉시 만들어낸다. Suno/Udio 같은 클라우드
보컬 생성기를 쓰고 싶은 사용자를 위한 프롬프트팩(`--suno`)도 지원한다.

## 절차

1. **요청 해석.** 사용자의 말에서 다음을 뽑아낸다 (모르면 합리적으로 추정하고,
   애매하면 한 번만 되물어본다):
   - `--genre`: `lofi`, `pop`, `edm`, `jazz`, `cinematic`, `acoustic`,
     `citypop`, `jpop`, `kpop` 중 하나 (모르면 `python3 -m composer genres` 로
     목록/특징 확인)
   - `--market`: 사용자가 "일본 시장용", "일본 플레이리스트 채널용", "미국
     타깃" 처럼 **특정 국가/시장**을 언급하면 `--genre` 대신(또는 함께)
     사용한다. `python3 -m composer markets` 로 지원 국가와 추천 장르·권장
     가사 언어를 확인한다. `--market` 만 주면 장르는 그 시장의 1순위
     추천으로 자동 선택된다.
   - `--mood`: 자유 텍스트 분위기 (예: "비 오는 밤", "신나는", "몽환적인")
   - `--key`: 예 "C major", "A minor" (생략 가능, 기본 C major)
   - `--tempo`: BPM (생략하면 장르 기본값)
   - `--length`: `short`(약 30~50초, 기본) 또는 `full`(풀 송 구조, 2분+)
   - `--seed`: 같은 곡을 재현하거나 "다른 버전으로 다시" 요청 시 시드를 바꿔서 사용

2. **해외 시장을 노리는 요청이면 `markets` 부터 확인한다.** "일본에서 잘
   먹힐 만한 곡", "해외 플레이리스트 채널용" 같은 요청은 `python3 -m
   composer markets` 결과를 사용자에게 먼저 보여주고 (추천 장르/가사 언어/
   시장 특성), 그중 하나를 고르게 하거나 1순위를 기본으로 진행한다. 가사는
   그 시장의 `lyric_language` 로 쓰는 것이 원칙이다 (예: 일본 시장이면
   일본어 가사 + 한국어/영어 병기).

3. **가사가 필요하면 Claude가 직접 쓴다.** 이 스킬은 노래를 부르는 보컬을
   합성하지 못한다(순수 신디사이저라 악기 사운드만 만든다). 사용자가 가사
   있는 노래/Suno용 결과를 원하면:
   - `python3 -m composer suno-prompt --genre ... --length short` 를 실행해
     각 섹션(`intro/verse/chorus/bridge/outro`)의 멜로디 음표 수를 참고하거나,
     `from composer.lyrics import syllable_budget` 로 섹션별 음표 수를 확인해
     음절 수를 대략 맞추다.
   - 가사를 `{"verse": ["줄1","줄2"], "chorus": [...], "bridge": [...]}`
     형태의 JSON으로 작성해 임시 파일로 저장한다 (예: `/tmp/lyrics.json`).
   - `create` 명령에 `--lyrics-json /tmp/lyrics.json --suno` 를 붙인다.

4. **곡 생성.**
   ```
   python3 -m composer create --genre lofi --mood "비 오는 밤" --key "D minor" \
       --length short --seed 42 --lyrics-json /tmp/lyrics.json --suno \
       --out my_song --outdir ./output
   ```
   해외 시장용이면 `--genre` 대신 `--market` 을 쓴다:
   ```
   python3 -m composer create --market japan --mood "노을 지는 퇴근길" \
       --lyrics-json /tmp/lyrics.json --suno --out my_song --outdir ./output
   ```
   기본으로 `./output/my_song.wav` 와 `./output/my_song.mid` 가 생성된다.
   `--suno` 를 주면 `./output/my_song.suno.txt` (Suno/Udio에 붙여넣을 프롬프트)도 생성되고,
   `--market` 을 줬다면 그 프롬프트에 `[Market]` 가이드 블록도 자동으로 들어간다.

5. **결과 보고.** 생성된 파일 경로, 장르/조성/템포/곡 구조, 재생 방법
   (오디오 플레이어로 wav 재생, DAW로 mid 열기)을 사용자에게 명확히 알려준다.
   Suno 프롬프트를 만들었다면 사용법(스타일 칸/가사 칸에 각각 붙여넣기)도 설명한다.

6. **반복 다듬기.** 사용자가 "더 신나게", "느리게", "다른 버전으로" 등을
   요청하면 `--tempo`, `--mood`, `--seed`(다른 정수로) 를 바꿔 다시 생성한다.
   전체 곡을 원하면 `--length full` 로 다시 생성한다.

## 참고

- 이 엔진은 100% 순수 파이썬 표준 라이브러리로만 동작한다 (numpy, FluidSynth,
  SoundFont, GPU 전부 불필요). 어떤 환경에서도 바로 실행된다.
- 장르 프리셋 구조와 다른 벤치마킹 도구와의 비교는 `docs/BENCHMARKS.md` 참고.
- 국가별 시장 추천 근거(리서치 출처 포함)는 `docs/MARKETS.md` 참고.
- 코드 구조는 `README.md` 의 "프로젝트 구조" 절 참고.
