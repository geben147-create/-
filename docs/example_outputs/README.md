# 예시 산출물

합성 테스트 곡을 파이프라인에 통과시켰을 때 실제로 나온 파일들입니다.
오디오 파일(WAV/FLAC/MIDI)은 저장소 크기 때문에 제외했고, 판단에 필요한 JSON·텍스트만 넣었습니다.
경로는 `<PROJECT>` 와 `<REPO>` 로 치환했습니다.

| 파일 | 무엇 |
|---|---|
| `project.json` | 원본 해시·목표 LUFS·권리 증빙 상태 |
| `analysis.json` | BPM·조성(수동 지정 기록 포함)·마디·구간·코드 (긴 배열은 생략) |
| `separation.json` | 분리 엔진과 스템 합산 검사 |
| `candidates.json` | 자동 생성한 15개 후보 |
| `human_decisions.json` | 무엇을 골랐고 어떤 음을 고쳤는지 (**이 데모는 `demo_auto`**) |
| `arrangement_manifest.json` | 적용된 선택·노트 수정·타임라인·마스터 체인 |
| `qc.json` | 전후 측정과 규격 검사 12항목 |
| `evidence_manifest.json` | 도구 버전·결정 요약·**경고 목록** |
| `evidence_AI_DISCLOSURE.txt` | 유통사 제출용 공시 초안 |
| `evidence_submission_checklist.json` | 제출 전 확인 11항목 |
| `evidence_tool_versions.json` | 사용한 라이브러리·바이너리 버전 |
| `evidence_file_hashes_sample.csv` | 전체 61행 해시 목록 중 앞부분 샘플 |
| `pipeline.log` | 실행 로그 |
