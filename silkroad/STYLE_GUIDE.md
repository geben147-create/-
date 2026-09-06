# 스타일 가이드 — 4종 비교

실크로드편 비주얼을 만들면서 네 방향을 실제로 생성해 봤다.
전부 **0크레딧**(구독 unlimited 등급 모델)으로 뽑았으므로 비용 없이 비교 가능하다.

전 스타일에 공통으로 유지한 채널 실측 규칙은 §5 에 정리했다.

---

## v1 — 다큐멘터리 사진사실 (잉카편 실측 그대로)

측정된 팔레트를 그대로 프롬프트에 넣은 버전. **채널 룩과 가장 가까움.**

```
cinematic AI history-documentary keyframe, painterly photoreal, 35mm anamorphic
character, strong atmospheric haze and layered depth, desaturated teal-slate
shadow palette (#1B3539 #33555D #5B767B #0B1818) with warm sand-bronze
highlights (#7A5F3E #B48352 #DFBF8F #392B1A), fine film grain
```

- 장점 — 기존 영상과 붙여도 이질감 없음. 실측 근거가 있는 유일한 버전
- 단점 — 저채도라 썸네일에서 눈에 덜 띔

## v2 — 고채도 초현실 바로크

```
surreal-romantic cinematic spectacle, richly saturated and luminous,
renaissance-baroque painterly quality fused with hyper-real detail, brilliant
turquoise and cyan against warm terracotta amber and gold, high saturation,
high key, volumetric god-rays, floating blossom petals and doves, ethereal
glow, epic scale, deep atmospheric layering, dreamlike and spectacular
```

- 장점 — 스펙터클. 썸네일 강함. 드론/직활강 샷과 잘 맞음
- 단점 — 실측 팔레트에서 가장 멂. 20분 내내 보면 피로함

## v3 — 수채·과슈 일러스트

```
delicate watercolour and gouache illustration, soft washes of dusty rose /
lavender / pale grey-blue / warm cream, muted desaturated pastel palette,
fine ink linework over translucent colour, wet-on-wet bleeding, visible paper
texture, soft atmospheric haze, small points of warm amber light against cool
tones, hand-painted romantic illustration, tranquil and poetic,
no harsh contrast, not photographic
```

- 장점 — **색 관계가 실측값과 오히려 잘 맞음**(한색 우세 + 작은 난색 하이라이트).
  감정 구간(미우나이)에 특히 강함. AI 얼굴 붕괴 문제가 구조적으로 사라짐
- 단점 — 스케일감·속도감 표현이 약함. 부산항/북극 같은 현대 구간과 안 어울릴 수 있음

## v4 — 인물 회화 (영웅 피규어 스터디)

```
painterly digital illustration, heroic classical figure study, richly rendered
ornate metalwork with fine engraved detail, flowing layered drapery with soft
fabric folds, dramatic rim lighting outlining the silhouette, strong
single-colour saturated background field with subtle painterly texture,
elegant and monumental, cinematic character art, digital oil painting quality
```

**색면 옵션 4가지** (레퍼런스의 진홍색 대신):

| 옵션 | 배경 색면 | 금속·림라이트 | 드레이퍼리 | 어울리는 인물 |
|---|---|---|---|---|
| A | 딥 틸 · 터쿼이즈 | 청동 | 크림·아이보리 | 미우나이 |
| B | 인디고 · 라피스 | 금 | 아이보리·도브그레이 | 호자 아흐라르 |
| C | 에메랄드 · 제이드 | 웨더드 청동 | 샌드·울 | 카라반 대상주 |
| D | 플럼 · 바이올렛 | 로즈골드 | 블러시·아이보리 | 미우나이와 딸 |

- 장점 — 인물을 강하게 세울 수 있음. **레퍼런스가 전부 뒷모습·투구라
  채널의 얼굴 회피 규칙과 충돌하지 않음**. 챕터 도입부 카드로 쓰기 좋음
- 단점 — 배경이 단색면이라 장면 전환(통과 전환)에 쓸 수 없음.
  **컷 소재가 아니라 인물 소개 카드용**

---

## 권장 — 섞어 쓰기

한 편을 한 스타일로 통일할 필요는 없다. 잉카편도 실제로는 실사 컷과
도해 컷(설산 X-ray 류)을 섞어 썼다.

| 대본 구간 | 권장 스타일 | 이유 |
|---|---|---|
| 0:00~1:40 미우나이 | **v3 수채** | 감정. 얼굴 문제 회피 |
| 1:40~3:20 연구·길 | **v1 다큐** | 사실성이 설득력을 만듦 |
| 3:20~5:05 아흐라르 | **v4 인물 카드** → **v2 스펙터클** | 인물 소개 후 자산 점등 최고점 |
| 5:05~7:15 부산·북극 | **v1 다큐** | 현대 실사. 저채도 몰락기 |
| 7:50~8:30 회수 | **v3 수채** | 처음과 같은 붓으로 닫음 |

이렇게 하면 **스타일 전환 자체가 시대 전환의 신호**가 된다.
과거는 그림, 현재는 사진. 관객이 설명 없이 알아챈다.

---

## §5 — 전 스타일 공통 유지 규칙 (실측 근거)

스타일이 바뀌어도 이건 안 바꾼다. 전부 잉카편 70,134프레임 계측값이다.

1. **난색 비율 서사 곡선** — 28% → 48% → **57%(정점)** → 10%(최저) → 57%(회복)
2. **통과 전환 25.4%** — 전경에 차폐물을 심어 화면 100% 덮이는 순간 컷.
   B 화이트아웃 6 · C 블랙아웃 8 · D 차폐물 와이프 4 = 18/71
3. **얼굴 예산 5% 미만** — 8분 30초 기준 상한 약 25초. 정면 얼굴 회피 7전략
4. **한색 우세** — 팔레트 점유율 한색 64.7% / 난색 35.3%.
   그림자는 채도 낮은 청록, 하이라이트만 난색
5. **장면 길이** — 잉카편 중앙값 11.8초. 8분 30초 편은 약 55컷 목표(중앙값 약 9초)

## 생성 조건

| | 모델 | 무료 설정 | 유료가 되는 지점 |
|---|---|---|---|
| 이미지 | `google/nano-banana-2` | 1K | 2K부터 5크레딧 |
| 이미지 | `bytedance/seedream-4-5` | **2K·4K 둘 다 무료** | — |
| 영상 | `kling-ai/kling-v3` | std / 5초 (multiShot도 무료) | pro 18, 10초 24 |
| 영상 | `minimax/minimax-h3` | 768p / 5초 | 6초부터 30, 2K 40 |
| 영상 | `alibaba/wan-v3-0-prime` | 480p / 5초 | 720p부터 45 |

**5초가 무료 상한선이다.** 6초만 돼도 과금된다. 동시 생성은 계정 전체 4개까지.
