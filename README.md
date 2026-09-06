# YH 4PC 클러스터 정비

4070 한 대에 몰려 있는 작업을 4대로 나누고, 400GB를 정리하는 작업 묶음.

## scripts/

| 파일 | 하는 일 | 안전성 |
|---|---|---|
| `01_YH_AUDIT.ps1` | CPU/RAM슬롯/VRAM/디스크/WSL/Docker/NVENC/네트워크/에디션 점검 | 읽기 전용 |
| `02_YH_DISK_RECLAIM.ps1` | 회수 가능한 캐시 용량 산출, vhdx 축소 안내 | 기본 조회만 (`-Apply` 필요) |
| `03_YH_REMOTE_BOOTSTRAP.ps1` | Tailscale · OpenSSH · RDP/RustDesk · 방화벽(Tailscale 대역 한정) | 관리자 권한 필요 |
| `04_YH_GDRIVE_ARCHIVE.ps1` | rclone copy → `rclone check` 검증 → 검증 후에만 원본 삭제 | 삭제 전 확인 프롬프트 |
| `05_WSL_LIMIT.ps1` | `.wslconfig` 메모리/CPU 상한 | **Hermes 이전 후에만** |

## docs/

- `01_REVIEW.md` — 계획 검토, 수정 9건 / 유지 7건
- `02_LOCAL_MODELS.md` — 8GB VRAM에서 실제로 되는 오픈소스 영상 모델
- `03_RUNBOOK.md` — 실행 순서와 금지 목록
- `YH_CLUSTER_BOARD.html` — 위 내용의 시각화 페이지

## 오늘 순서

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\01_YH_AUDIT.ps1        # 4대 전부
powershell -ExecutionPolicy Bypass -File .\scripts\02_YH_DISK_RECLAIM.ps1 # 메인, 조회만
```

그다음 4개 `YH_AUDIT_*` 폴더를 한곳에 모으면 각 PC의 역할을 숫자로 확정할 수 있다.

## 금지

D: 삭제/포맷 · `wsl --unregister` · Vault 네트워크 이동 ·
`docker system prune --volumes` · `rclone sync` · 검증 전 원본 삭제
