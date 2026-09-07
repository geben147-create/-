# AI 파생곡 재편곡·QC·증빙 파이프라인 (stayfade)

Suno 같은 AI 생성곡에서 출발한 트랙을 **사람이 결정하는 재편곡 → 보컬 보정 → 믹스·마스터 → 기술 QC → 증빙 패키지**로
만드는, 실제로 돌아가는 로컬 파이프라인입니다. 모든 도구는 무료입니다.

📖 **[단계별 튜토리얼 — 바로 보기](https://claude.ai/code/artifact/73bf272c-77a8-4765-92c0-875b6afed09a)**
(저장소 파일: [`docs/index.html`](docs/index.html) · GitHub에서 바로 렌더:
[htmlpreview](https://htmlpreview.github.io/?https://github.com/geben147-create/-/blob/claude/stay-with-fade-qc-jktund/docs/index.html))
📋 **[실행 점검표 세 장](docs/checklist.html)** — 승인 기여 순위별 한 것/안 한 것, 항목별 실행 방법과 유료 대안, 세 세션 비교
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

```powershell
# Windows — 설치 후 한 줄. 사람이 고를 차례가 되면 알아서 멈춥니다
powershell -ExecutionPolicy Bypass -File skill\scripts\install_windows.ps1
powershell -ExecutionPolicy Bypass -File skill\scripts\run_windows.ps1 -Audio "C:\Users\나\Music\곡.wav" -Name mysong -Key Ebm
```

```bash
# macOS / Linux
bash skill/scripts/install_linux_mac.sh
bash skill/scripts/run_unix.sh ~/Music/곡.wav mysong Ebm
```

### 단계별로 직접 실행하려면

설치 스크립트는 가상환경을 `~/stayfade-venv` (Windows: `%USERPROFILE%\stayfade\.venv`) 에 만듭니다.
그 안의 파이썬을 직접 부르거나, 먼저 `source ~/stayfade-venv/bin/activate` 로 활성화하세요.

```bash
export PYTHONPATH=$PWD/pipeline
PY=~/stayfade-venv/bin/python          # Windows: %USERPROFILE%\stayfade\.venv\Scripts\python.exe

$PY -m stayfade --project ./work/mysong init 원본.wav --title "곡 제목" --artist "이름"
$PY -m stayfade --project ./work/mysong analyze          # 조성이 모호하면 --key Ebm 로 지정
$PY -m stayfade --project ./work/mysong candidates
$PY -m stayfade --project ./work/mysong gate             # ⏸ 여기서 멈춤 — 듣고 고르세요
$PY -m stayfade --project ./work/mysong build
$PY -m stayfade --project ./work/mysong qc
$PY -m stayfade --project ./work/mysong evidence

$PY skill/scripts/validate.py ./work/mysong              # 스키마 + 기여 검증
```

## 검증된 실행 결과

합성 테스트 곡(Ebm, 112 BPM, 87.7초)으로 전 단계 완주한 결과입니다. 원본 음원은 저장소에 포함하지 않았습니다.

| 측정 | 원본 | 편곡·마스터 |
|---|---|---|
| 길이 | 87.71초 | 112.86초 |
| LUFS-I | −9.67 | −14.01 |
| True Peak | **+1.28 dBTP** | **−1.00 dBTP** |
| Crest | 10.35 dB | 14.80 dB |
| LRA | 3.4 LU | 11.25 LU |
| 스테레오 상관 | 0.8319 | 0.9029 |
| DC 오프셋 | 0.0021 | 0.0000076 |
| 앞뒤 무음 | 0 / 1.15초 | 0 / 0초 |
| 규격 검사 | — | **PASS** (실패 0 · 경고 0) |

보컬 체인 검증: 일부러 30 cents 어긋나게 만든 테이크 → 보정 후 **9.2 cents** (6음 감지, 5음 보정).
측정은 하모니를 끈 리드를 스테레오 전체 모노 합으로 잰 중앙값입니다. 하모니를 켜고 재면 19.2 cents,
한쪽 채널만 재면 0.8 cents 로 보입니다 — 뒤의 두 방식은 실제 튠 정확도를 나타내지 않습니다.
결정 파일에 적힌 노트 수정 5건이 전부 오디오에 반영되었습니다(이 데모의 `decided_by` 는 `demo_auto` 이므로 사람이 고른 것이 아닙니다).
증빙에는 요청한 개수가 아니라 실제로 반영된 개수만 기록됩니다.

전체 수치: [`docs/demo_results.json`](docs/demo_results.json)

## 테스트

```bash
PYTHONPATH=pipeline ~/stayfade-venv/bin/python pipeline/tests/test_pipeline.py
```

35개 단위 테스트가 통과합니다. 리미터 릴리스 수식이 기준 재귀식과 1e-9 dB 이내로 일치하는지,
마스터가 트루피크 천장을 지키는지, 크로스페이드가 등파워인지, 드럼 합성이 프로세스가 달라도 같은지,
사람이 지정한 노트 수정이 실제로 반영되는지, 결정 파일이 비면 관문이 막히는지,
보컬 정렬이 첫 소리를 지우거나 딱 소리를 만들지 않는지, 스키마가 실제 산출물을 받아들이는지를 검사합니다.

## 구조

```
pipeline/stayfade/     파이프라인 코드 (common, synth, analyze, separate, transcribe,
                       variants, midiio, render, vocal, mix, qc, evidence, human_gate, cli)
pipeline/tests/        합성 테스트 곡 생성기 + 단위 테스트
skill/SKILL.md         재사용 스킬 (언제 멈춰야 하는지 포함)
skill/schema/          산출물 6종 JSON Schema
skill/scripts/         설치 스크립트 + 검증기
skill/templates/       결정 파일 · 녹음 체크리스트 · 가사 이력 양식
docs/index.html        단계별 튜토리얼
```

## 독립 검토

만든 결과물을 재현성 · 오디오 DSP · 견고성 · 스키마 · 문서 · 정직성 여섯 갈래로 나눠 따로 검토했고,
재현해서 확인된 결함 40여 건을 고쳤습니다. 대표적인 것:

- 같은 시드인데도 실행할 때마다 다른 마스터가 나오던 문제 (드럼 합성이 프로세스마다 달라지는 `hash()` 사용)
- 인트로 앞 1.6초가 통째로 무음이던 문제
- 등파워라고 적어놓고 등이득 곡선을 써서 이음매마다 3 dB 꺼지던 문제
- 리미터가 트루피크 천장을 넘기던 문제, 목표 음량을 못 맞추고도 맞춘 것처럼 기록하던 문제
- 문서에 있는 `transpose_range` 노트 수정이 조용히 실패하던 문제
- 공시 문서가 실제 반영된 수정이 아니라 요청한 수정을 세던 문제
- 결정 파일이 비어 있어도 사람 결정 관문을 통과하던 문제
- AI 공시 초안이 기계가 고른 것을 “사람이 결정한 것”으로 적던 문제 (지금은 경고 블록과 함께 사실대로 적습니다)
- 녹음 파일 경로가 틀렸는데도 공시에 “인간 실연 있음”으로 적히던 문제
- 튜토리얼의 보컬 수치가 한쪽 채널만 잰 값이라 실제보다 좋아 보이던 문제

같은 결함이 다시 들어오지 않도록 회귀 테스트를 붙였습니다.

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
