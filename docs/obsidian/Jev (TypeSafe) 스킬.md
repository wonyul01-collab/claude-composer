---
title: Jev (TypeSafe) 스킬
aliases: [Jev, TypeSafe, typesafe-ai]
tags: [claude-composer, skill, jev, typesafe, ai]
created: 2026-09-26
source: .claude/skills/typesafe-ai/SKILL.md
status: 연결 준비
---

# Jev (TypeSafe) 스킬

> [!info] 저장 위치
> 원본 스킬: `claude-composer/.claude/skills/typesafe-ai/SKILL.md`
> 공식 문서: https://docs.typesafe.ai/llms.txt (구현 전 반드시 최신 문서 확인)

## 한 줄 요약
**Jev**는 TypeSafe의 첫 System One 모델. 자연어 + 앱 상태를 받아 글을 생성하지 않고
**타입이 있는 판단과 확률**을 돌려준다. 워크플로는 코드가 쥐고, 모델은 "프로그래밍
가능한 상식"만 제공한다.

## 3가지 기본 단위 (Primitive)
| 필요 | Primitive | 핵심 |
| --- | --- | --- |
| 정해진 목록 중 하나 | **Choice** | 옵션 간 확률 분포 |
| 조건이 참인가? | **Noul** | yes 확률 (0.5 = 반반, "중간 강도" 아님) |
| 어느 정도인가? | **Score** | 순서 있는 레벨 위 확률 가중 위치 |

## 설계 원칙
- 질문 하나 = 좁고 일관된 판단 하나. 독립적인 차원은 나눈다.
- **state**(원문, 정책, 현재 사실)는 이름 있는 JSON 필드로, **instructions**에 판단,
  **criteria**에 가능한 답을 정의한다. 질문 ID는 모델에 전달되지 않는다.
- "해당 없음" 선택지를 넣는다. 후보에 없는 값은 고를 수 없다.
- 같은 state에 대한 독립 질문은 **한 번에 병렬**로 묻는다.
- 확률·confidence 임계값은 실제 데이터로 검증한다. 타입 보장 ≠ 정답 보장.
- API 키는 서버 쪽에만 둔다.

## 활용 패턴
- **라우팅 + 인자 채우기**: 요청 → 핸들러 + 타입 파라미터 선택
- **생성 대신 선택**: 코드가 후보를 만들고 Jev가 고름
- **근거 찾기/판단**: 리랭킹, 계층 분류
- **판단을 재사용 데이터로**: 차원별 Score → 코드에서 가중치/정렬
- **검증 후 에스컬레이션**: 불확실하면 사람/추론 모델로
- **변하는 상태에 반응**: 관찰 사실과 추론 상태 구분

## Claude Composer 연결 계획
[[Claude Composer]]의 엔진은 순수 파이썬이고, 지금은 사람이 `--genre`, `--mood`,
`--market` 등을 직접 골라야 한다. Jev를 붙일 자리:

- [ ] **자연어 요청 → 파라미터 라우팅** (Choice): "비 오는 밤 퇴근길 일본 감성"
      → `genre`(9개 + 해당없음), `market`, `length` 선택. `key`는 major/minor Choice.
- [ ] **템포/에너지** (Score): "잔잔 ↔ 신나는" 레벨 → 장르 기본 BPM 범위 안에서 코드가 매핑
- [ ] **가사 검증** (Noul): 시장 `lyric_language` 준수 여부, 섹션 음절 수 적합 여부
- [ ] **여러 seed 후보 랭킹** (Score): 곡 메타데이터 + 요청 무드 일치도로 상위 버전 추천
- [ ] **불확실하면 되묻기**: confidence 낮을 때만 사용자에게 한 번 질문

구현 방향: `composer/jev.py`에 얇은 어댑터 → `composer.api.compose()` 앞단에 붙이고,
키가 없으면 현재 규칙 기반 동작으로 자동 폴백.

## 관련
- [[Claude Composer]]
- [[음악플레이리스트 스튜디오]]
