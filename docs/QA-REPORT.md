# 검수 결과 (10번 체크리스트)

`pipeline/qa.js` 를 실제 Chromium으로 돌린 결과입니다. 눈으로 본 게 아니라
브라우저에 물어본 값입니다. 재현:

```bash
python3 -m http.server 8811 --bind 127.0.0.1 --directory site &
npm i playwright-core
node pipeline/qa.js /tmp/qa
```

## 통과한 항목

```
1920px  overflow=0  layers=0  attrs=0  console=0  pin=ok bar=41.66%
1440px  overflow=0  layers=0  attrs=0  console=0  pin=ok bar=41.66%
1024px  overflow=0  layers=0  attrs=0  console=0  pin=ok bar=41.68%
 768px  overflow=0  layers=0  attrs=0  console=0  pin=ok bar=55.56%
 390px  overflow=0  layers=0  attrs=0  console=0
 360px  overflow=0  layers=0  attrs=0  console=0
short window 1440x580: hero copy bottom=557 vh=580  fits
reduced-motion: videos hidden=true sources attached=false stills shown=true

no problems found
```

| 체크 | 어떻게 검증했나 | 결과 |
|---|---|---|
| 화면 · PC/모바일 | 6개 폭에서 `scrollWidth - clientWidth` | 전부 0 — 가로 스크롤 없음 |
| 레이어 · z-index | 모든 `.stage` 의 `isolation` 계산값 + video/scrim/copy z-index 순서 | 전부 통과 |
| stacking context | 각 `.stage` 의 **모든 조상**에서 `transform`·`filter`·`opacity<1`·`will-change` 검사 | 위반 0 |
| 재생 · 자동재생 | 모든 `<video>` 의 `muted`·`playsinline`·`poster` 속성 유무 | 누락 0 |
| 성능 · 콘솔 | 콘솔 에러 수집 (미디어 네트워크 에러 제외 — 아래 참고) | 0 |
| 핀 | 스크럽 섹션을 화면에 물린 뒤 600px 스크롤, 섹션 top 좌표 변화 측정 | 이동 2px 미만 = 핀 정상 |
| 스크럽 | 스크롤 후 진행 바 width 확인 | 0% → 41.66% 로 실제 전진 |
| 접근성 · 모션 | `reducedMotion: 'reduce'` 컨텍스트 | 영상 display:none, **소스 자체를 안 붙임**, 정지 이미지 노출 |
| 창 높이 | 1440×**580** 뷰포트에서 히어로 카피 bottom 좌표 | 557 < 580 — 잘리지 않음 |

## 검수 중 실제로 잡은 버그 하나

1440×580(노트북 + 북마크바 + 확장프로그램)에서 **히어로 카피가 화면 밖으로
밀려났습니다**(bottom 833 > vh 580). 원인은 `min-height:100vh` 가 아니라
`.hero__copy { max-width: 48ch }` 였습니다.

`ch` 는 **그 요소 자신의 font-size** 기준입니다. 카피 컨테이너의 폰트는 17px이라
48ch ≈ 408px 밖에 안 됐고, 그 좁은 칸에 68px 헤드라인이 들어가면서 3줄로
찢어져 히어로 높이가 폭발한 것입니다.

`max-width: min(46rem, 100%)` 로 바꾸고 `@media (max-height:700px)` 축소
규칙을 더해 해결했습니다. **이건 눈으로는 못 잡습니다** — 짧은 뷰포트를
실제로 띄워봐야 나옵니다. 가이드 10번이 "가장 많이 놓치는 것"이라고 적은
바로 그 항목입니다.

## 이 환경에서 검증하지 **못한** 것

- **렌더 자체의 화질과 구도.** 이 컨테이너는 이그레스 정책상
  `videocdn.pollo.ai` 에 접근할 수 없어 생성된 이미지·영상을 한 번도
  열어보지 못했습니다. 프롬프트에 세이프존(중앙 26%)과 "컷 없음"을 명시했지만,
  모델이 실제로 지켰는지는 **확인 못 했습니다.**
  `pipeline/PROMPTS.md` 의 detail 링크로 직접 보시고, 어긋난 컷만 재생성하세요.
- **가독성 · 최악 프레임.** 영상이 로드되지 않아 실제 프레임 위 대비를 재지
  못했습니다. 스크림 알파는 `pipeline/contrast.py` 의 **이론적 최악값**
  (순검정 프레임) 기준이라 실측보다 보수적입니다 — 즉 실제로는 더 여유가 있습니다.
- **iOS Safari 실기기 자동재생.** 시뮬레이션으로는 대체 불가입니다.
- **Lighthouse LCP.** 미디어가 로컬화된 뒤에 측정해야 의미가 있습니다.

미디어 네트워크 에러를 콘솔 집계에서 제외한 이유가 이것입니다. 이 환경에서
막힌 호스트라서 나는 에러이고, 코드 결함이 아닙니다.
`pipeline/fetch-media.sh` 로 로컬화한 뒤 다시 돌리면 그 필터 없이도 0이어야
합니다.
