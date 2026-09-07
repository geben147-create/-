---
name: stayfade-arrange
description: AI 생성곡(Suno 등) 파생 트랙을 사람이 결정하는 재편곡·보컬 보정·마스터·기술 QC·증빙 패키지로 만드는 반복 가능한 파이프라인. 스템 분리, 자동 채보, 드럼/베이스/코드/브리지 A·B·C 후보 생성, 사람 결정 관문, 믹스·마스터, LUFS/True Peak/상관/DC 측정, 해시·AI 공시 초안까지. 사용자가 새 곡을 같은 방식으로 처리하려 할 때, 유통 제출용 기술 규격을 맞출 때, 또는 인간 창작 기여 기록을 남기려 할 때 사용.
---

# stayfade — AI 파생곡 재편곡·QC·증빙 스킬

## 이 스킬이 하는 일과 하지 않는 일

**한다**: 스템 분리 · BPM/키/섹션/코드 추정 · 자동 채보 · 편곡 후보 A/B/C 생성 · 미리듣기 렌더 ·
사람 결정 적용 · 보컬 튠/타이밍/노이즈/EQ/컴프 · 구조 재조립 · 믹스 · 마스터 · 기술 QC · 해시/매니페스트/공시 초안.

**하지 않는다**: 저작권을 만들어내지 않는다. 유통 승인을 보장하지 않는다. AI 출처를 숨기지 않는다.
사람이 부르거나 연주한 것을 대신해주지 않는다. 전체 청취를 대신하지 않는다.

## 언제 멈춰야 하는가 (중요)

1. **06 human_gate**: `human_decisions.json` 의 `status` 가 `DECIDED` 가 아니면 진행 금지.
2. `decided_by` 가 `human` 이 아니면(예: `demo_auto`) 산출물을 **인간 창작 증거로 제시하지 말 것**. 증빙 경고에 자동으로 표시된다.
3. 조성 추정이 `ambiguous: true` 면(나란한조 혼동) 사용자에게 확인받고 `analyze --key` 로 지정할 것. 틀린 조성으로 편곡하면 전곡이 불협이 된다.
4. 권리 증빙(생성 서비스 영수증·구독 상태·곡 URL·생성일)이 없으면 제출 단계로 넘어가지 말 것.

## 한 번에 실행 (권장)

```powershell
# Windows — 사람 결정 앞에서 자동으로 멈추고, 미리듣기 폴더와 결정 파일을 열어 줍니다
powershell -ExecutionPolicy Bypass -File skill\scripts\run_windows.ps1 -Audio "C:\Users\나\Music\곡.wav" -Name mysong -Key Ebm
```

```bash
# macOS / Linux
bash skill/scripts/run_unix.sh ~/Music/곡.wav mysong Ebm
```

결정 파일을 채운 뒤 같은 명령을 다시 실행하면 이어서 끝까지 진행합니다.

## 실행 순서 (단계별로 직접)

```bash
export PYTHONPATH=/path/to/pipeline
python -m stayfade --project ./work/<곡이름> init <원본.wav> --title "곡 제목" --artist "이름" \
    --target-lufs -14 --side-gain 1.0 --distributor routenote \
    --source-description "Suno Pro 생성 (플랜·생성일 기입)" --rights-evidence "영수증 파일 경로"
python -m stayfade --project ./work/<곡이름> analyze          # 01 분리 + 02 분석 + 03 채보
python -m stayfade --project ./work/<곡이름> analyze --key Ebm  # 조성이 모호하다고 나오면 지정
python -m stayfade --project ./work/<곡이름> candidates       # 04 후보 + 05 미리듣기
python -m stayfade --project ./work/<곡이름> gate             # 06 사람 결정 관문 (여기서 멈춤)
#  → 04_render/*.wav 를 전부 듣고 human_decisions.json 을 채운다
python -m stayfade --project ./work/<곡이름> build            # 07 보컬 + 08 믹스·마스터
python -m stayfade --project ./work/<곡이름> qc               # 09 측정 + A/B
python -m stayfade --project ./work/<곡이름> evidence         # 10 증빙
```

`all` 은 gate 에서 자동으로 멈춘다.

## 폴더 규약

```
00_original  원본(수정 금지) + SHA-256      05_edit      새 파트 WAV/MIDI, 보컬 보정본
01_stems     분리 스템(원본 멀티트랙 아님)  06_mix       프리마스터
02_midi      자동 채보(참고용, 창작물 아님)  07_master    마스터 WAV / 유통용 FLAC
03_variants  후보 MIDI                      08_qc        측정 + A/B
03_human_raw 사람이 녹음한 원본(보존)        09_evidence  해시·도구·매니페스트·공시 초안
04_render    후보 미리듣기 WAV
```

## 사람이 반드시 하는 일 (자동화 불가)

| 단계 | 사람이 하는 것 | 왜 |
|---|---|---|
| 후보 선택 | A/B/C 중 고르기 | 음악적 판단 |
| 노트 수정 | `note_edits` 로 최소 몇 개 직접 고치기 | 고르기만 하면 기여가 약함 |
| 허밍/멜로디 | 새 멜로디를 직접 흥얼거려 녹음 | 자동 초안보다 훨씬 강한 창작 증거 |
| 가창/연주 | 실제 녹음 | 실연 기여는 대체 불가 |
| 전체 청취 | 처음부터 끝까지 | 수치 검사로 대체 불가 |
| 권리 증빙 | 영수증·구독·곡 URL 수집 | 유통 심사 1순위 |

## 노트 수정 문법 (`note_edits`)

```json
{"op":"transpose","index":12,"semitones":-1}
{"op":"transpose_range","from":8,"to":12,"semitones":-2}
{"op":"delete","index":7}
{"op":"move","index":3,"delta_sec":0.04}
{"op":"velocity","index":5,"value":110}
{"op":"length","index":5,"value":0.35}
{"op":"add","start":12.5,"dur":0.5,"pitch":51,"velocity":100}
```

## 스키마

`schema/` 안의 JSON Schema 로 산출물을 검증한다.

```bash
python skill/scripts/validate.py ./work/<곡이름>
```

| 파일 | 스키마 |
|---|---|
| `project.json` | `schema/project.schema.json` |
| `analysis.json` | `schema/analysis.schema.json` |
| `candidates.json` | `schema/candidates.schema.json` |
| `human_decisions.json` | `schema/human_decisions.schema.json` |
| `arrangement_manifest.json` | `schema/arrangement_manifest.schema.json` |
| `qc.json` | `schema/qc.schema.json` |

## 코드를 고쳤다면 테스트부터

```bash
PYTHONPATH=pipeline python pipeline/tests/test_pipeline.py     # 21개 단위 테스트, 약 1분
```

리미터·엔벌로프의 수식 정확성, 트루피크 천장 준수, 하모니 클리핑, 후보 재현성,
노트 수정 문법, 스키마 적합성, 조성 파싱을 검사합니다.

## 기술 규격 (제출 직전 각 유통사 공식 페이지에서 재확인)

- RouteNote: 스테레오 **FLAC 또는 MP3 320kbps, 16bit/44.1kHz**, WAV 업로드 불가. 앞뒤 무음 8초 초과 금지, 클리핑 금지.
- 일반 권장: True Peak ≤ -1.0 dBTP, LUFS-I -16 ~ -9 (스토어 정규화 기준이 다르므로 곡에 맞게), DC ≈ 0.

## 자주 나는 오류

| 증상 | 원인 | 대처 |
|---|---|---|
| `demucs` 실패 | 모델 가중치 다운로드 차단/미설치 | 자동으로 HPSS 폴백. 품질 낮으므로 로컬에서 demucs 재시도 |
| 키가 나란한조로 잘못 | 구성음이 같음 | `analyze --key Ebm` 로 지정 |
| 마디가 늦게 시작 | 드럼 없는 인트로 | 자동으로 0초까지 그리드 연장됨. 어긋나면 `--beats-per-bar` 조정 |
| 보컬 보정이 부자연 | 반음 이상 어긋난 음 | 보정 한계. 재녹음이 빠름 |
| `⛔ 아직 실행하지 않은 단계가 있습니다` | 단계를 건너뜀 | 메시지가 알려주는 명령을 먼저 실행 |
| `⛔ 조성을 해석할 수 없습니다` | `--key` 표기 오류 | `Ebm` `Gb` `C#m` 형식으로. 단조는 뒤에 `m` |

오류가 나면 같은 명령에 `--debug` 를 붙이면 전체 추적 정보가 나옵니다.
실행 기록은 프로젝트 폴더의 `pipeline.log` 에 쌓입니다.
