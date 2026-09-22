# 영상 분석 & 벤치마킹 리서치

## 1. 요청받은 유튜브 영상에 대해 — 솔직한 한계 고지

`https://youtu.be/KRgylv32KSE` 영상 자체를 "포렌식"(자막/화면 분석)하려고
시도했지만, 이 작업 환경에서는 `youtube.com` 으로의 접속이 네트워크 정책상
차단되어 있고, 영상 ID로 제목·자막·설명을 웹 검색으로도 찾아내지 못했다
(비공개 처리되었거나 색인이 안 된 것으로 추정). 즉 **이 영상의 실제 내용을
직접 보고 분석하지는 못했다.** 추측으로 내용을 지어내지 않기 위해, 대신
"Claude(Code)로 음악을 만드는" 공개된 실제 프로젝트/스킬들을 폭넓게
조사해서 그 영상이 다뤘을 법한 접근 방식들을 파악하고, 그 결과를 이 프로그램
설계에 반영했다. 영상 링크를 다시 확인해 제목/채널명을 알려주시면, 그
채널이 실제로 어떤 방식(로컬 GPU 모델? 클라우드 API? 순수 코드 합성?)을
썼는지 좁혀서 추가로 맞춰볼 수 있다.

## 2. 조사한 벤치마킹 대상

| 프로젝트 | 방식 | 강점 | 한계 |
|---|---|---|---|
| [AgriciDaniel/claude-music](https://github.com/AgriciDaniel/claude-music) | Claude Code 스킬 + **ACE-Step 1.5**(로컬 diffusion 오디오 모델)를 직접 호출. 웹 대시보드 포함, 11개 서브스킬(generate/cover/repaint/enhance 등) | 보컬이 있는 완성곡을 15초~수분 내 생성, 장르 커버·섹션 리페인트 등 완성도 높은 프로덕션 기능 | **NVIDIA GPU 필수**(최소 4GB, 권장 8GB+), 모델 다운로드 ~5GB, CPU만 있는 환경(지금 이 작업 환경 포함)에서는 사실상 못 씀 |
| [tubone24/midi-agent-skill](https://github.com/tubone24/midi-agent-skill) | 텍스트 → 구조화 JSON → `midiutil` 로 MIDI 생성 → FluidSynth + SoundFont 로 WAV 렌더 | GPU 불필요, 128개 GM 악기 지원 | FluidSynth 바이너리와 SoundFont(.sf2, 보통 수십~수백 MB) 를 사용자가 별도 설치해야 함 |
| [sirruf/music-gen-skill](https://github.com/sirruf/music-gen-skill) / "code-to-music" 계열 | `music21`(음악이론)+`mido`(MIDI 후처리)로 알고리즘 작곡, Electronic 파이프라인(신스 직접 합성)과 Traditional 파이프라인(SoundFont) 이원화 | 음악 이론 기반이라 화성이 안정적, 장르별 파이프라인 분리 아이디어가 좋음 | `music21` 이 program_change 를 안정적으로 내보내지 않아 `mido` 로 후처리해야 하는 등 접합 지점이 까다로움 |
| "Generative Music Composer" (skills.lc 배포) | L-system/문맥자유문법 기반 리듬, 마르코프 체인 멜로디, 보이스리딩 제약을 둔 화성 엔진 | 절차적 생성 깊이가 상당함(적응형/게임 음악에 적합) | 배포 방식이 스킬 마켓플레이스에 종속, 오디오 렌더링 자체보다 "생성 로직"에 집중 |
| [bitwize-music-studio/claude-ai-music-skills](https://github.com/bitwize-music-studio/claude-ai-music-skills), Suno Music Creator 스킬류 | Claude가 가사/스타일 태그(`[Verse]`, `[Chorus]` 등)를 작성해 **Suno**에 붙여넣는 "프롬프트 엔지니어링" 워크플로우 | 사람 목소리로 부르는 완성곡을 얻을 수 있음, LLM이 라임/스토리 구조를 잘 짬 | Suno/Udio 계정·크레딧 필요(클라우드 종속), 로컬에서 즉시 결과물이 안 나옴 |

## 3. Claude Composer가 위 리서치에서 가져온 설계 결정

1. **로컬 GPU/외부 설치 의존성 제거** — `claude-music`(ACE-Step)과
   `midi-agent-skill`(FluidSynth+SoundFont) 두 방식 모두 "설치"가 필요해서
   컴퓨터에 익숙하지 않은 사용자에게는 진입장벽이 크다. 그래서 Claude
   Composer는 **오디오 합성기 자체를 파이썬 표준 라이브러리만으로 새로
   작성**했다 (`composer/synth.py`). `pip install` 한 줄도 필요 없다.
2. **MIDI도 함께 내보낸다** — `midi-agent-skill`/`code-to-music` 계열에서
   확인한 대로, MIDI 파일이 있으면 사용자가 나중에 개러지밴드·FL
   Studio·MuseScore 등에서 악기를 바꾸거나 편집할 수 있다. `composer/midiwriter.py`
   가 외부 라이브러리 없이 표준 MIDI 포맷 1 파일을 직접 써서, program_change
   같은 "music21이 실수하는 지점"도 처음부터 mido 없이 직접 제어한다.
3. **음악 이론 기반 절차적 생성** — "Generative Music Composer"의 마르코프
   체인/화성 규칙 아이디어를 채택해, 장르별 코드 진행 풀 + 스케일/코드톤에
   가중치를 둔 랜덤워크 멜로디(`composer/arranger.py`)로 화성적으로
   말이 되는 멜로디를 만든다. 시드를 고정하면 같은 곡을 재현할 수 있다.
4. **보컬이 필요하면 Suno/Udio 경로를 열어둔다** — 순수 코드 합성으로는
   사람 목소리를 만들 수 없으므로, `bitwize-music-studio`류 스킬에서 쓰는
   `[Style]` / `[Verse]` / `[Chorus]` 태그 포맷을 그대로 따라
   `composer/suno_prompt.py` 가 Suno·Udio에 바로 붙여넣을 수 있는 프롬프트팩을
   만든다. Claude가 직접 쓴 가사를 넣을 수도 있다. 즉, **악기 트랙은 즉시
   로컬에서, 보컬이 필요하면 클라우드로** — 두 접근을 하나의 명령으로 잇는다.
5. **GPU가 있는 사용자를 위한 업그레이드 경로** — 나중에 이 프로젝트를
   더 키우고 싶다면, `claude-music`(ACE-Step) 처럼 로컬 diffusion 모델을
   선택적으로 붙이는 것도 자연스러운 다음 단계다. 이는 "설치 없이 바로
   되는 기본값" 위에 "GPU 있으면 더 좋아지는 옵션"을 얹는 구조라, 지금
   만든 순수 파이썬 엔진을 갈아엎지 않고도 확장할 수 있다.
