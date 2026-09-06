# 전체 파이프라인 — 이 홈페이지는 실제로 이렇게 만들어진다

시네마틱 스크롤 사이트를 **샷 설계 → 첫 프레임 → 영상 생성 → 인코딩 → 웹 조립 →
텍스트 레이어 → 검수** 순서로 실제로 만든 결과물입니다.
사이트의 내용이 곧 사이트의 제작 방법이고, 본문에 적힌 규칙이 그대로 이 페이지가
돌아가는 규칙입니다.

```
site/
  index.html            섹션 구조 · 가이드 01~10 전문
  assets/style.css      레이어 계약, 스크림, 타이포 스케일
  assets/app.js         매니페스트 배선 · 지연 로딩 · 스크럽 (외부 의존 0)
  media/sources.js      GENERATED — 클립별 local/remote 주소 한 곳

pipeline/
  contrast.py           스크림 알파 대비비 계산 (표의 숫자가 여기서 나옴)
  make_manifest.py      site/media/sources.js 생성기 — 클립 목록의 단일 원본
  fetch-media.sh        원격 클립 내려받기 → 인코딩 → local 로 전환
  encode.sh             용도별 ffmpeg 패스 + 클립별 용량 예산 검사
  PROMPTS.md            사용한 모델 · 설정 · 실제 과금 · 프롬프트 전문
```

## 보는 법

```bash
python3 -m http.server 8000 --directory site
# http://localhost:8000
```

`file://` 로 열어도 동작합니다. 매니페스트를 `fetch()` 가 아니라 `<script>` 로
읽는 이유가 그것입니다.

## 미디어가 어디에 있는가

`site/media/sources.js` 는 클립마다 **local 과 remote 두 칸**을 들고 있고,
맨 위의 `use` 가 어느 칸을 읽을지 정합니다.

- `use: "remote"` — 지금 상태. Pollo CDN에서 바로 재생합니다. 저장소에 영상
  바이트가 없어도 페이지가 완성된 모습으로 돕니다.
- `use: "local"` — `pipeline/fetch-media.sh` 를 돌리면 자동으로 바뀝니다.
  원본을 내려받아 `encode.sh` 로 웹용 인코딩까지 마친 뒤 로컬 파일을 읽습니다.

```bash
pipeline/fetch-media.sh      # 내려받기 + 인코딩 + use:"local" 전환
pipeline/encode.sh s1-hero   # 한 클립만 다시 인코딩
```

> 이 저장소를 만든 컨테이너는 이그레스 정책상 `videocdn.pollo.ai` 에 접근할 수
> 없었습니다. 그래서 생성은 MCP로 하고, 내려받기·인코딩은 스크립트로 분리해
> 두었습니다 — CDN에 닿는 환경에서 `fetch-media.sh` 한 줄이면 로컬화됩니다.

## 이 빌드가 원문 가이드와 다른 세 곳

1. **극성이 반대입니다.** 참조 아트디렉션이 밝은 화이트 톤이라, 스크림은
   `#F7F7FA`, 글자는 `#0E1116`, 최악 프레임은 순백이 아니라 **순검정**입니다.
   계산 방법은 같고 입력만 뒤집었습니다 — `pipeline/contrast.py`.

2. **원문 대비비 표를 다시 계산했습니다.** 같은 방식으로 원문 조건을 재현하면
   알파 0.58에서 **4.47:1** 이 나옵니다. 원문이 적은 4.72:1 이 아니고,
   본문 기준 4.5:1 에 미달합니다. 그래서 이 빌드의 본문 하한선은 **0.62** 입니다.

3. **스크럽에 GSAP을 쓰지 않습니다.** 네이티브 `position:sticky` + `scroll` 로
   같은 동작을 냅니다. CDN 의존이 사라지고, 원문이 경고하는
   "`transform` 걸린 조상 안의 `position:fixed`" 함정 자체가 발생하지 않습니다.
   대신 새 함정이 하나 생기는데 — 조상에 `overflow-x:hidden` 이 걸리면
   `overflow-y` 가 `auto` 로 계산돼 sticky 가 조용히 깨집니다.
   그래서 `body` 는 `overflow-x: clip` 을 씁니다.

## 레이어 계약

```
.stage { isolation: isolate }     ← 여기서 stacking context 를 의도적으로 만든다
  ├─ video   z-index: 0
  ├─ scrim   z-index: 1
  └─ copy    z-index: 2          ← 9999 가 필요한 순간은 오지 않는다
```

조상에 `transform` · `filter` · `opacity<1` · `will-change` 를 걸지 마세요.
걸리는 순간 이 계약이 깨지고, 그게 "글씨가 영상 뒤로 들어가는" 진짜 원인입니다.
