# 실행 순서

## 오늘 (파괴적 작업 없음)

1. 4대 전부에서 audit 실행 — 아무것도 변경하지 않음
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\01_YH_AUDIT.ps1
   ```
2. 메인 PC에서 회수 가능 용량 조회 (조회만)
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\02_YH_DISK_RECLAIM.ps1
   ```
3. 4개 `YH_AUDIT_*` 폴더를 메인 PC 한 곳에 모음

이 3개가 끝나야 "i3를 AUTO로, i7을 STORE로" 같은 배치를 숫자로 확정할 수 있다.

## 1~2일차

4. 캐시 실제 삭제 → `02_YH_DISK_RECLAIM.ps1 -Apply`
5. WSL/Docker vhdx 축소 (스크립트가 안내하는 diskpart 절차, 수동)
6. 남은 용량 재측정. 여기서 이미 목표 달성이면 구글드라이브 이전 자체가 불필요할 수 있음
7. 보조 PC 원격 세팅 → `03_YH_REMOTE_BOOTSTRAP.ps1 -Role AUTO|FINISH|STORE`
8. Tailscale 로그인 (사람), SSH 키 등록

## 3일차 이후

9. 아카이브만 구글드라이브로 → `04_YH_GDRIVE_ARCHIVE.ps1` (copy → -Verify → -DeleteSourceAfterVerify)
10. PC 간 대용량 이전은 Tailscale 아닌 LAN robocopy:
    ```powershell
    robocopy "D:\AI_DATA\archive" "\\YH-STORE\d$\AI_DATA\archive" /E /Z /MT:16 /R:2 /W:5 /LOG:C:\move.log
    ```
11. Hermes/n8n/Docker 이전 (백업 → 신규 설치 → 48~72시간 검증 → 구 인스턴스 정지)
12. 전부 옮긴 뒤에만 → `05_WSL_LIMIT.ps1`

## 절대 안 하는 것

- D: 삭제/포맷, 파티션 변경
- `wsl --unregister`
- Obsidian Vault를 네트워크 드라이브로 이동
- `docker system prune --volumes` (n8n/DB 데이터 소멸)
- `rclone sync` (대상 파일을 지움 — 반드시 `copy`)
- 검증 전 원본 삭제
