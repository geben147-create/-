# 4PC 클러스터 계획 검토

## 측정된 것 / 측정 안 된 것

| 대상 | 상태 |
|---|---|
| Claude Code 원격 컨테이너 | **측정 완료** — Xeon 4 vCPU @2.1GHz, RAM 15GB, 디스크 252GB(여유 30GB), **GPU 없음**, Ubuntu 24.04, Docker 있음, ffmpeg/rclone 없음 |
| 사용자의 Windows PC 4대 | **측정 불가** — 클라우드 컨테이너라 사용자 하드웨어가 보이지 않음. `scripts/01_YH_AUDIT.ps1` 을 각 PC에서 실행해야 함 |

원문의 "지금 이 컴퓨터"는 두 가지로 갈린다.
- 채팅이 도는 컨테이너: 위 사양. **GPU가 없으므로 영상 생성 불가.**
- 사용자가 앉아 있는 Windows PC: 오직 audit 스크립트로만 확인 가능.

---

## 수정 필요 항목

### C1. Pollo Ultra 구독이 이미 있음 (가장 큰 누락)

계정 확인 결과:
- 플랜: Ultra (연간), 상태 active, 2027-08-31까지
- 잔여 크레딧: 12,040
- 이 세션에 Pollo MCP 서버 연결됨 → Claude Code에서 직접 생성 가능

Pollo 카탈로그에 포함된 것: Veo 3.1, Sora 2 / 2 Pro, Kling v3, Seedance 2.5,
MiniMax Hailuo 2.3 / minimax-h3, Wan 3.0, Runway Gen-4, Nano Banana Pro, Flux 2,
Midjourney v8, Topaz / Pollo 업스케일, video-extend, ref2video, face-swap.

**결론:** 8GB VRAM 노트북 GPU로 이 중 어느 것도 재현할 수 없다.
로컬 영상 생성 클러스터를 짓기 전에, 이미 결제된 크레딧을 먼저 쓰는 것이 맞다.

### C2. MiniMax / Pollo 오픈소스 여부

| | 오픈소스 | 로컬 실행 |
|---|---|---|
| MiniMax LLM (M1/M2, Text-01, VL-01) | O (Apache 2.0 계열) | X — MoE 수백B, 8GB VRAM 불가 |
| MiniMax 영상 (Hailuo / video-01) | **X** — 가중치 비공개 | X — API 전용 |
| Pollo AI | **X** — 자체 모델 없는 SaaS 취합 서비스 | X |

Pollo는 "오픈소스가 있나?"의 답이 없음이다. 다만 **이미 구독 중이므로 API로 전부 접근 가능**하다.

### C3. Hermes Agent 관련 기술 주장은 미검증

원문의 `hermes gateway install`, Windows 네이티브 지원, `hermes backup` 등은
인용된 GitHub 링크로 확인되지 않았다. 이 위에 4대 아키텍처 전체를 얹기 전에
실제 저장소/문서에서 명령어 존재 여부를 먼저 확인할 것.

### C4. 400GB 이전 — 순서가 틀렸다

이동 전에 **삭제**가 먼저다. 통상 회수되는 것:
HuggingFace 캐시, pip/npm 캐시, WSL·Docker `.vhdx` (파일을 지워도 vhdx는 안 줄어듦),
죽은 프로젝트의 `node_modules`, Windows Update 캐시.
경험상 100~200GB가 옮길 필요 없이 사라진다. → `scripts/02_YH_DISK_RECLAIM.ps1`

그 다음에야 구글드라이브. 그리고 **구글 드라이브 데스크톱(스트리밍)은 쓰지 말 것** —
로컬 캐시가 C:를 다시 채우고 랜덤 읽기가 느려 ComfyUI/모델 용도로 최악이다.
`rclone` + 해시 검증(`rclone check`) → 검증 통과 후 원본 삭제. → `scripts/04_YH_GDRIVE_ARCHIVE.ps1`

구글드라이브에 **보내면 안 되는 것**: 활성 git 저장소, ComfyUI/LTX 모델 가중치,
Obsidian Vault 원본, Docker 볼륨.

### C5. Tailscale — 용도를 잘못 잡았다

- **PC 간 400GB 일괄 이전**: Tailscale 쓰지 말 것. 같은 공유기에 물린 기가비트 LAN에서
  `robocopy /MIR /Z /MT:16` 또는 SMB가 더 빠르고 단순하다. Tailscale은 WireGuard 암복호화가
  끼고, 직결(direct)에 실패하면 DERP 릴레이로 떨어져 훨씬 느려진다.
- **평상시 원격 접속/조종**: Tailscale이 정답. 포트포워딩 없이 SSH·RDP를 안전하게 연결한다.

즉 Tailscale은 *이전 도구*가 아니라 *상시 운영 도구*다.

### C6. ffmpeg / hyperframe "공유"는 성립하지 않는다

`hyperframe`은 HTTP/2 라이브러리(h2·httpx 의존성)로 수십 KB짜리 pip 패키지다.
`ffmpeg`도 100MB 남짓 단일 바이너리다. 네트워크로 공유할 대상이 아니다.

- 파이썬 의존성 → `pip freeze > requirements.txt` (또는 `uv`)로 재현. 각 PC에 재설치.
- ffmpeg → `winget install Gyan.FFmpeg` 로 각 PC에 설치.
- 진짜 공유 대상은 **모델 가중치와 미디어 파일**이며, 그것도 SMB로 20GB 모델을 매번 읽으면
  느리므로 자주 쓰는 모델은 각 PC 로컬 NVMe에 복제한다.
- 다른 PC의 성능이 필요한 것이라면 파일 공유가 아니라 **SSH 원격 실행 / 작업 큐**가 답이다.

### C7. GTX 1650에 인코딩을 맡기기 전에 확인할 것

GTX 1650은 리비전에 따라 NVENC 세대가 다르고, 일부 초기 TU117 모델은 NVENC이 없다.
배정 전에 실행: `ffmpeg -hide_banner -encoders | findstr nvenc`

또한 i9 CPU의 libx264 가 GTX 1650 NVENC보다 화질/용량 효율이 좋은 경우가 많다.
"약한 PC에 인코딩" 은 자동으로 옳은 배치가 아니다. 실제로 한 번 재보고 정할 것.

### C8. 원격 접속 스택 과설계

Tailscale + RustDesk + SSH를 첫날 전부 깔 필요 없다.
- Windows **Pro** → Tailscale + 내장 RDP + SSH. RustDesk 불필요.
- Windows **Home** → RDP 호스트가 없으므로 RustDesk 필요.

에디션은 audit 결과에서 나온다. 그리고 SSH/RDP 방화벽은 전체 개방이 아니라
Tailscale 대역(`100.64.0.0/10`)으로 제한한다. → `scripts/03_YH_REMOTE_BOOTSTRAP.ps1`

### C9. Windows SSH 관리자 계정 함정

관리자 그룹 계정은 `~/.ssh/authorized_keys` 가 **무시된다**.
키는 `C:\ProgramData\ssh\administrators_authorized_keys` 에 넣어야 한다.

---

## 유지해야 할 항목

- 읽기 전용 점검을 먼저 하고 그 결과로 역할을 정하는 순서
- COPY → 검증 → 그다음 원본 정리 (MOVE 선행 금지)
- 오늘 WSL/Ubuntu 삭제 금지, 파티션 변경 금지
- D: 볼륨 레이블 "UBUNTU 24_0" 과 WSL 배포판은 별개라는 지적
- Obsidian Vault를 단일 원본으로 두고 네트워크 드라이브에 올리지 않는 것
- 활성 프로젝트(`D:\AI_PROJECTS`)를 빠른 NVMe에 유지
- 4070을 "전부 하는 PC"에서 "작업용 PC"로 되돌린다는 방향 자체
- Hermes 이전을 백업 → 신규 설치 → 검증 → 구 인스턴스 정지 순으로 하는 것
