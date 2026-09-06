# AI 파생곡 재편곡·QC·증빙 파이프라인 (stayfade)

Suno 같은 AI 생성곡에서 출발한 트랙을 **사람이 결정하는 재편곡 → 보컬 보정 → 믹스·마스터 → 기술 QC → 증빙 패키지**로
만드는, 실제로 돌아가는 로컬 파이프라인입니다. 모든 도구는 무료입니다.

📖 **[단계별 튜토리얼 (HTML)](docs/index.html)** — 설치부터 제출 준비까지, 실행 결과 수치 포함
📦 **[재사용 스킬](skill/SKILL.md)** — 다음 곡도 같은 절차로

---

## 이 저장소가 하는 일

| 단계 | 내용 | 누가 |
|---|---|---|
| 00 | 원본 보존 + SHA-256 | 🤖 |
| 01 | 스템 분리 (demucs → 실패 시 HPSS 폴백) | 🤖 |
| 02 | BPM · 조성 · 마디 · 구간 · 코드 추정 (나란한조 모호성 경고 포함) | 🤖 |
| 03 | Basic Pitch 자동 채보 (참고용) | 🤖 |
| 04 | 드럼·베이스·코드·브리지·구조 **A/B/C 후보** 생성 | 🤖 |
| 05 | 후보 미리듣기 렌더 (numpy 신스, 샘플 팩 불필요) | 🤖 |
| 06 | **사람 결정 관문** — 여기서 멈춤 | 🎤 |
| 07 | 보컬 노이즈·튠·타이밍·디에서·EQ·컴프·하모니 | 🤖 |
| 08 | 구조 재조립 + 스템 부분 감산 + 마스터 체인 | 🤖 |
| 09 | LUFS / LRA / True Peak / 상관 / DC / 무음 / 포맷 검사 + A/B 파일 | 🤖 |
| 10 | 해시 · 도구 버전 · 결정 이력 · AI 공시 초안 | 🤖 |

`06`에서 `human_decisions.json`의 `status`가 `DECIDED`가 아니면 진행을 거부합니다.
`decided_by`가 `human`이 아니면 증빙에 **"인간 창작 증거로 쓸 수 없음"**이 자동으로 기록됩니다.

## 빠른 시작

```bash
bash skill/scripts/install_linux_mac.sh          # 또는 skill/scripts/install_windows.ps1
export PYTHONPATH=$PWD/pipeline

python -m stayfade --project ./work/mysong init 원본.wav --title "곡 제목" --artist "이름"
python -m stayfade --project ./work/mysong analyze          # 조성이 모호하면 --key Ebm 로 지정
python -m stayfade --project ./work/mysong candidates
python -m stayfade --project ./work/mysong gate             # ⏸ 여기서 멈춤 — 듣고 고르세요
python -m stayfade --project ./work/mysong build
python -m stayfade --project ./work/mysong qc
python -m stayfade --project ./work/mysong evidence

python skill/scripts/validate.py ./work/mysong             # 스키마 + 기여 검증
```

## 검증된 실행 결과

합성 테스트 곡(Ebm, 112 BPM, 87.7초)으로 전 단계 완주한 결과입니다. 원본 음원은 저장소에 포함하지 않았습니다.

| 측정 | 원본 | 편곡·마스터 |
|---|---|---|
| 길이 | 87.71초 | 112.86초 |
| LUFS-I | −9.67 | −14.00 |
| True Peak | **+1.28 dBTP** | **−1.83 dBTP** |
| Crest | 10.35 dB | 13.93 dB |
| 스테레오 상관 | 0.8319 | 0.8532 |
| DC 오프셋 | 0.0021 | 0.0000113 |
| 규격 검사 | — | **PASS** (실패 0 · 경고 0) |

보컬 체인 검증: 일부러 30 cents 어긋나게 만든 테이크 → 보정 후 **9.2 cents** (6음 감지, 5음 보정).

전체 수치: [`docs/demo_results.json`](docs/demo_results.json)

## 구조

```
pipeline/stayfade/     파이프라인 코드 (common, synth, analyze, separate, transcribe,
                       variants, midiio, render, vocal, mix, qc, evidence, human_gate, cli)
pipeline/tests/        합성 테스트 곡 생성기
skill/SKILL.md         재사용 스킬 (언제 멈춰야 하는지 포함)
skill/schema/          산출물 6종 JSON Schema
skill/scripts/         설치 스크립트 + 검증기
skill/templates/       결정 파일 · 녹음 체크리스트 · 가사 이력 양식
docs/index.html        단계별 튜토리얼
```

## 하지 않는 것

- 저작권을 만들어내지 않습니다.
- 유통 승인을 보장하지 않습니다.
- **AI 출처를 숨기지 않습니다.** 탐지 회피 목적의 가공은 지원하지 않습니다.
- 사람이 부르거나 연주한 것을 대신하지 않습니다.
- 전체 청취를 대신하지 않습니다.

## 알아둘 정책 (2026-09-06 기준, 제출 직전 재확인 필요)

- RouteNote는 AI 콘텐츠를 **한국 파트너 스토어(멜론·지니·벅스·FLO·VIBE)·Amazon·Content Recognition**에 배포하지 않습니다.
- 한국음악저작권협회는 2026-08-03 AI 활용 음악 등록 기준을 만들었다가 **2026-08-25 철회**했습니다.
- YouTube Content ID는 레퍼런스에 대한 **배타적 권리**를 요구합니다.

출처와 전체 설명은 [튜토리얼](docs/index.html)에 정리했습니다.
