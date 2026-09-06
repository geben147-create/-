# music MCP stack

MCP 서버 3개를 **한 번에 전역 설치**하고, 컴퓨터에 깔린 **모든 MCP 클라이언트**
(Claude Code · Codex · Cursor · Claude Desktop · Windsurf · VS Code · LM Studio ·
Gemini CLI)에 자동 등록한 다음, **실제 MCP 핸드셰이크로 검증**까지 하는 설치 스택입니다.

"설치했다"가 아니라 "서버를 띄우고 프로토콜로 말을 걸어서 툴 개수를 세었다"까지가 검증입니다.

---

## 뭐가 깔리나

| 서버 | 툴 | 하는 일 | REAPER 필요 |
|---|---:|---|---|
| `music-toolkit` | **9** | 오디오 QC · BPM/키 검출 · 구간 분할 · 허밍→MIDI · 스템 분리 · 유통 마스터링 · 제작기록(해시) | ✕ |
| `reaper-twelvetake` | **176** | REAPER 제어 (믹싱 · 마스터링 · MIDI 작곡) | 툴 호출 시 ○ |
| `reaper-xdarkzx` | **182** | REAPER 제어 (편집 · QC · ReaScript 자동화) | 툴 호출 시 ○ |
| | **367** | | |

`music-toolkit`은 이 저장소에 들어 있는 자체 서버입니다. DAW 없이 돌기 때문에
Codex든 Cursor든 어디서든 그대로 동작합니다.

### music-toolkit 툴 9개

| 툴 | 설명 |
|---|---|
| `list_capabilities` | 어떤 기능이 이 컴퓨터에서 실제로 되는지 보고 (빠진 의존성을 이름으로 알려줌) |
| `audio_qc` | 길이 · 샘플레이트 · 채널 · 피크 · 트루피크 · LUFS · DC 오프셋 · 클리핑 · 앞뒤 무음 → 유통 기준 통과 여부 |
| `detect_tempo_key` | BPM + 키 (Krumhansl-Schmuckler). 2등과의 점수 차까지 주므로 확신도를 알 수 있음 |
| `detect_sections` | 인트로/벌스/후렴/브릿지 경계를 타임코드로 |
| `audio_to_midi` | 허밍·노래를 MIDI로 (Spotify Basic Pitch) |
| `split_stems` | 보컬/드럼/베이스/기타 분리 (Demucs) |
| `prefetch_models` | Demucs·Basic Pitch 모델 가중치를 미리 받아둠 |
| `make_distribution_master` | 스테레오 FLAC 16bit/44.1kHz + R128 라우드니스 정규화, 결과 QC 리포트 동봉 |
| `provenance_manifest` | 모든 파일의 SHA-256 · 타임스탬프 · 툴 버전 · 창작 결정 로그 → JSON + CSV |

---

## 설치

### macOS / Linux

```bash
git clone https://github.com/geben147-create/-.git
cd -/mcp-stack

./install.sh                    # 기본: 코어 오디오 + REAPER 서버 2개 (약 350MB)
./install.sh --full             # + Demucs, Basic Pitch (수 GB, torch 포함)
./install.sh --full --prefetch  # + 모델 가중치까지 미리 다운로드
./install.sh --reaper-bridge    # + REAPER에 Lua 브릿지 설치
```

### Windows (PowerShell)

```powershell
git clone https://github.com/geben147-create/-.git
cd -\mcp-stack

.\install.ps1
.\install.ps1 -Full -Prefetch
.\install.ps1 -ReaperBridge
```

설치 위치는 macOS·Linux가 `~/.local/share/music-mcp`,
Windows가 `%LOCALAPPDATA%\music-mcp` 입니다. `MUSIC_MCP_HOME` 으로 바꿀 수 있습니다.

**설치가 끝나면 MCP 클라이언트를 재시작하세요.** 설정 파일은 시작할 때만 읽습니다.

---

## 검증

```bash
python3 ~/.local/share/music-mcp/verify.py
```

```
MCP verification  (servers.json)
--------------------------------------------------------------------------
SERVER                STATUS    TOOLS  DETAIL
--------------------------------------------------------------------------
music-toolkit         PASS          9  music-toolkit v1.29.1 (MCP 2025-06-18)
reaper-twelvetake     PASS        176  twelvetake-reaper-mcp v1.29.1 (MCP 2025-06-18)
reaper-xdarkzx        PASS        182  ReaperMCP v1.29.1 (MCP 2025-06-18)
--------------------------------------------------------------------------
3/3 passed
```

`verify.py`는 목록만 읽는 게 아니라 서버를 **실제로 실행해서** `initialize` →
`tools/list` 를 주고받고 툴 개수를 셉니다. 개수가 기대치보다 적으면 FAIL 입니다
(예: xDarkzx 서버는 `[analysis]` 확장이 빠지면 조용히 182 → 175로 줄어듭니다).

클라이언트 설정 파일에 실제로 뭐가 적혔는지 확인하려면:

```bash
python3 ~/.local/share/music-mcp/verify.py --client codex
python3 ~/.local/share/music-mcp/verify.py --client claude-code
```

---

## 클라이언트별 설정 위치

| 클라이언트 | 파일 | 키 |
|---|---|---|
| Claude Code | `~/.claude.json` | `mcpServers` |
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.*]` |
| Cursor | `~/.cursor/mcp.json` | `mcpServers` |
| Claude Desktop | macOS `~/Library/Application Support/Claude/claude_desktop_config.json`<br>Windows `%APPDATA%\Claude\...`<br>Linux `~/.config/Claude/...` | `mcpServers` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` |
| VS Code / Copilot | macOS `~/Library/Application Support/Code/User/mcp.json`<br>Windows `%APPDATA%\Code\User\mcp.json`<br>Linux `~/.config/Code/User/mcp.json` | `servers` (+ `type: stdio`) |
| LM Studio | `~/.lmstudio/mcp.json` | `mcpServers` |
| Gemini CLI | `~/.gemini/settings.json` | `mcpServers` |

기존 설정은 보존됩니다. 파일을 처음 건드리기 전에 `.bak` 백업을 만들고, 다른 서버 항목과
사용자 설정(Codex의 주석·`model`·`[tui]` 등)은 그대로 둡니다. 여러 번 실행해도 중복이
생기지 않습니다 — 테스트로 고정해 두었습니다.

```bash
python3 configure_clients.py --list             # 이 컴퓨터에서 감지된 클라이언트
python3 configure_clients.py --client cursor    # 하나만
python3 configure_clients.py --all              # 감지 안 된 것까지 전부
./install.sh --uninstall                        # 모든 클라이언트에서 제거
```

---

## Codex에서 쓰기

설치가 `~/.codex/config.toml`에 이렇게 씁니다:

```toml
[mcp_servers.music-toolkit]
command = "/Users/you/.local/share/music-mcp/venv/bin/python"
args = ["/Users/you/.local/share/music-mcp/music_toolkit/server.py"]
```

절대경로라서 Codex를 어느 디렉터리에서 띄우든 동작합니다. 그 다음 Codex에게 그냥
`"이 WAV의 BPM하고 키 알려줘"`, `"유통용 마스터로 뽑고 QC 돌려줘"` 라고 하면 됩니다.

---

## REAPER 서버 쓰기

REAPER 서버 2개는 **REAPER가 안 떠 있어도 툴 목록은 나옵니다** (그래서 검증이 통과합니다).
하지만 실제로 툴을 **호출**하려면 REAPER가 열려 있고 브릿지 Lua 스크립트가 돌고 있어야 합니다.

```bash
twelvetake-reaper-mcp --install-bridge
```

그 다음 REAPER에서 `Actions → Show action list → Load ReaScript` 로
`reaper_mcp_bridge.lua` 를 불러 실행하세요.

---

## 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| 클라이언트에 서버가 안 보임 | 클라이언트를 재시작하세요. 설정은 시작 시에만 읽습니다 |
| `verify.py`가 `not found` | `~/.local/bin` 이 PATH에 없습니다. 셸 rc에 `export PATH="$HOME/.local/bin:$PATH"` 추가 |
| `split_stems`가 가중치 다운로드 실패 | `dl.fbaipublicfiles.com` 접근이 막힌 환경입니다. 열린 네트워크에서 `prefetch_models` 를 한 번 실행하면 `~/.cache/torch/hub/checkpoints` 에 캐시됩니다 |
| xDarkzx 서버 툴이 175개 | `[analysis]` 확장이 빠졌습니다. `uv tool install --force "xdarkzx-reaper-mcp[analysis]"` |
| REAPER 툴이 호출 시 타임아웃 | REAPER가 꺼져 있거나 브릿지 Lua가 안 돌고 있습니다 |
| `--full` 설치가 수 GB | 기본 PyPI torch 휠이 CUDA 라이브러리를 끌고 옵니다. 설치 스크립트가 CPU 전용 인덱스를 먼저 시도하고, 막히면 기본으로 폴백합니다 |

---

## 테스트

```bash
python3 tests/test_config_writer.py    # 설정 파일 병합·삭제·멱등성
python3 tests/test_music_toolkit.py    # numpy 직렬화 · 툴 등록
```

두 테스트 모두 실제로 발견된 버그를 고정합니다: 설정 삭제 시 뒤따르는 사용자 섹션이
함께 지워지던 정규식 버그, 그리고 numpy 스칼라가 MCP 응답 직렬화를 깨뜨리던 버그.

---

## 출처

- TwelveTake reaper-mcp — https://github.com/TwelveTake-Studios/reaper-mcp
- xDarkzx Reaper-MCP — https://github.com/xDarkzx/Reaper-MCP
- Basic Pitch — https://github.com/spotify/basic-pitch
- Demucs — https://github.com/facebookresearch/demucs
- REAPER — https://www.reaper.fm/download.php
