"""stayfade — 자동 편곡·QC·증빙 파이프라인 (Suno 파생곡 → 인간 결정 기반 재편곡).

단계 (steps):
  00 layout     원본 보존 + SHA-256 + 폴더 생성
  01 separate   스템 분리 (demucs 우선, 실패 시 hpss 폴백)
  02 analyze    BPM / 키 / 마디 / 섹션 / 코드 추정
  03 transcribe Basic Pitch 로 bass / vocals / other → MIDI (참고용)
  04 variants   드럼·베이스·코드·브리지·구조 A/B/C 후보 생성 (AI 후보, 확정 아님)
  05 render     numpy 신스 / fluidsynth 로 미리듣기 렌더
  06 human_gate human_decisions.json 이 PENDING 이면 정지. 사람이 고르고 고치면 적용
  07 vocal      사람이 녹음한 보컬 테이크(있을 때만) 정리·정렬·보정
  08 mixmaster  구조 재조립 + 믹스 + 마스터 (HPF / M-S / 4x 오버샘플 리미터 / LUFS)
  09 qc         LUFS-I / LRA / True Peak / DC / 상관 / 무음 / 클리핑 / 포맷
  10 evidence   해시 / 도구 버전 / 매니페스트 / AI 공시 초안
"""
__version__ = "0.1.0"
