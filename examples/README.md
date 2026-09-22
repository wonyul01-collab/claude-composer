# 데모곡

`python3 -m composer create` 로 실제 생성한 샘플입니다. 재현하려면 아래 표의 명령을 그대로 실행하면 됩니다 (시드 고정이라 항상 같은 결과가 나옵니다).

| 파일 | 장르 | 조성/템포 | 재현 명령 |
|---|---|---|---|
| `demo_lofi.wav` / `.mid` | lofi | D minor, 77 BPM | `python3 -m composer create --genre lofi --mood "비 오는 밤" --key "D minor" --seed 42 --length short --out demo_lofi --outdir ./examples` |
| `demo_pop.wav` / `.mid` | pop | C major, 110 BPM | `python3 -m composer create --genre pop --mood "신나는" --key "C major" --seed 7 --length short --out demo_pop --outdir ./examples` |
| `demo_edm.wav` / `.mid` | edm | A minor, 127 BPM | `python3 -m composer create --genre edm --mood "파티" --key "A minor" --seed 21 --length short --out demo_edm --outdir ./examples` |

`.wav`는 바로 재생, `.mid`는 DAW(개러지밴드, FL Studio, MuseScore 등)에서 열어 편집할 수 있습니다.
