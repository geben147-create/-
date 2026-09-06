# Pollo 무료(0크레딧) 모델 검증 지도

계정: Ultra 연간 구독 (`isSubscriber: true`, `isActive: true`)
검증일: 2026-09-06 · 방법: `pollo_estimate_generation_cost` (견적은 크레딧을 소모하지 않음)

판정 기준은 정가(`cost`)가 아니라 **실제 차감액 `discountCost`** 입니다.
`activityMode: "unlimited"` + `discount: 100` + `discountCost: 0` 인 조합만 무료로 취급합니다.

## 무료 확정 — 이미지

| brand | model | 정가 | discountCost | activityMode |
|---|---|---|---|---|
| `google` | `nano-banana-2` | 5 | **0** | unlimited |
| `bytedance` | `seedream-4-5` | 4 | **0** | unlimited |
| `bytedance` | `seedream-5-lite` | 4 | **0** | unlimited |

## 무료 확정 — 영상 (설정 고정)

무료는 모델 단위가 아니라 **설정 단위**입니다. 아래 파라미터를 벗어나면 즉시 유료로 전환됩니다.

| brand | model | 무료 설정 | 정가 | discountCost |
|---|---|---|---|---|
| `minimax` | `minimax-h3` | `resolution: 768P`, `duration: 5` | 50 | **0** |
| `kling-ai` | `kling-v3` | `mode: std`, `duration: 5` | 30 | **0** |
| `alibaba` | `wan-v3-0-prime` | `resolution: 480p`, `duration: 5` | 25 | **0** |

## 유료 전환 경계선 (검증됨 — 사용 금지)

| 모델 | 변경한 설정 | discountCost | activityMode |
|---|---|---|---|
| `minimax-h3` | `duration: 6` | 30 | discount |
| `kling-v3` | `mode: pro` | 18 | discount |
| `kling-v3` | `duration: 10` | 24 | discount |
| `wan-v3-0-prime` | `resolution: 720p` | 45 | normal |
| `google/nano-banana-2-lite` | 기본 | 2 | discount |
| `bytedance/seedream-5-0-pro` | 기본 | 2 | discount |

**결론: 영상 3종 모두 5초가 무료 상한선입니다.** 해상도 상향(2K/720p)과
품질 모드 상향(pro)도 전부 과금 대상입니다.

## 브라우저(Playwright) 경로가 불가능한 이유

이 실행 환경의 네트워크 정책상 `pollo.ai` 는 연결이 차단됩니다:

```
https://pollo.ai       -> 000 (connection failed)
https://pollo.ai/login -> 000 (connection failed)
```

Chromium 자체는 `/opt/pw-browsers` 에 설치돼 있지만, 도메인에 도달할 수 없으므로
로그인 화면조차 렌더링되지 않습니다. 브라우저 자동화는 선택지가 아닙니다.

또한 속도 면에서도 브라우저 경로가 불리합니다. MCP 도구는 Pollo 생성 API를
직접 호출하므로 로그인 · DOM 대기 · 업로드 위젯 조작 단계가 전부 사라지고,
한 번의 응답에서 여러 생성 작업을 동시에 제출할 수 있습니다.

## 운영 규칙

1. 생성 전 반드시 `pollo_estimate_generation_cost` 로 `discountCost` 를 확인한다.
2. `discountCost > 0` 이면 제출하지 않는다.
3. 영상은 `numOutputs: 1` 로 제출한다 — 과금은 출력물 단위이므로
   배치는 무료 한도를 벗어날 수 있다.
