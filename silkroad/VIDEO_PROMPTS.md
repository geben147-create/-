# 실크로드 편 — 영상 프롬프트 설계서

8분 30초 / 11 HERO 컷 / 딥 호라이즌 실측 규격 적용

이 문서의 모든 스타일 수치는 추정이 아니라 **잉카편 70,134프레임 전수 계측값**에서 가져왔다.
출처: `data/palette.json`, `data/metrics.json`, `data/scenes_verified.json`

---

## 0. 적용한 채널 실측 규격

### 0-1. 팔레트 — 틸-앤-탠

k-means 10색 실측. 한색 64.7% + 난색 35.3%.

| HEX | 점유율 | H | S | V | 역할 |
|---|---|---|---|---|---|
| `#1B3539` | 16.7% | 188 | 53 | 22 | 그림자 기본 |
| `#33555D` | 14.1% | 191 | 45 | 36 | 중간 한색 |
| `#5B767B` | 13.1% | 189 | 26 | 48 | 대기 원근 |
| `#0B1818` | 11.0% | 180 | 54 | 9 | 최암부 |
| `#8C9D9B` | 9.8% | 173 | 11 | 62 | 안개·하늘 |
| `#7A5F3E` | 8.3% | 33 | 49 | 48 | 흙·나무 |
| `#494636` | 8.2% | 51 | 26 | 29 | 중간 난색 |
| `#B48352` | 7.1% | 30 | 54 | 71 | 청동·석양 |
| `#DFBF8F` | 6.4% | 36 | 36 | 87 | 최명부 하이라이트 |
| `#392B1A` | 5.3% | 33 | 54 | 22 | 난색 그림자 |

**규칙** — 그림자는 항상 채도 낮은 청록으로, 하이라이트만 모래·청동으로.
회색 그림자 금지. 이게 이 채널의 지문이다.

### 0-2. 난색 비율 서사 곡선

잉카편 실측: 황금기 36.6~56.9%(중앙 51.7) → 몰락기 7.8~19.7% → 유산 56.9% 회복.
**실크로드 편에 그대로 이식한 매핑:**

| 대본 구간 | 감정 | 목표 난색비율 | 광원 지시 한 줄 |
|---|---|---|---|
| 0:00~0:50 미우나이 | 버려짐 | **28~30%** | `cold pre-dawn blue, single warm oil lamp` |
| 0:50~2:35 카라반사라이·물 | 발견 | **40~48%** | `dusty ochre daylight, warm interior firelight` |
| 3:20~5:05 아흐라르 | **황금기 정점** | **50~57%** | `warm golden hour, low raking sun` |
| 5:05~7:15 부산·북극 | 몰락·냉각 | **10~15%** | `cold overcast, blue hour, steel and ice` |
| 7:50~8:30 편지 회수 | 회복 | **57%** | `warm golden dawn, amber recovery` |

곡선의 절대값이 아니라 **모양**이 규격이다. 정점 → 붕괴 → 회복.

### 0-3. 전환 유형 배분 (잉카편 실측 71건)

| 유형 | 실측 | 비율 | 실크로드 편 목표(약 55컷) |
|---|---|---|---|
| A. 하드컷 | 37 | 52.1% | 29 |
| E. 크로스 디졸브 | 13 | 18.3% | 10 |
| C. 블랙아웃 통과 (아치·터널·야간) | 8 | 11.3% | 6 |
| B. 화이트아웃 통과 (구름·안개) | 6 | 8.5% | 5 |
| D. 차폐물 와이프 (벽·인물·연기) | 4 | 5.6% | 3 |
| F. 앵글 전환 (동일 장소) | 3 | 4.2% | 2 |

**통과 전환(B+C+D) = 18/71 = 25.4%** ← 보고서 헤드라인 수치.
B+C만 세면 14/71 = 19.7%. 두 수치 다 맞다. 정의가 다를 뿐이다.

> **핵심 원리** — 서로 다른 시드에서 나온 AI 클립 두 개를 이어붙이는 문제를,
> **이어붙일 정보 자체를 없애서** 해결한다. 카메라가 차폐물 속으로 들어가
> 화면이 100% 덮이는 순간에 컷을 바꾼다. 차폐물만 갈아끼우면 어떤 주제에도 이식된다.

### 0-4. 얼굴 예산

잉카편 실측: 이름 있는 인물 정면 얼굴 19분 중 **5회 / 약 25초(2%)**,
무명 인물 포함해도 **약 51초(4.4%)**. 러닝타임의 5% 미만.

**미우나이는 정면 얼굴을 쓰지 않는다.** 회피 7전략:
머리 자르기 · 사물 인서트 · 후면 샷 · 실루엣 · 모션 블러 · 극소형 배치 · 양식화 초상.
8분 30초 기준 얼굴 예산 상한 = **약 25초**.

### 0-5. 장면 길이

잉카편 실측 72장면: 평균 16.2초 / 중앙값 11.8초 / p10 1.7초 / p90 39.0초.
19분 29초에 확정 72개(추정 115).

실크로드 편은 8분 30초(510초)에 **약 55컷 목표 → 중앙값 약 9초.**
잉카편보다 빠르게 간다. 대본이 짧은 문장 → 질문 → 부분답 리듬이라 컷이 더 자주 끊겨야 한다.

---

## 1. HERO 11컷 — 시작 프레임 + 카메라 무브 + 나가는 전환

각 컷은 **이미지 = 무브의 시작 프레임**으로 설계됐다.
전경 차폐물은 통과 전환용으로 일부러 심어 놨다.

---

### H1 · 0:00~0:12 · 도착하지 못한 편지
**난색 30% · 나가는 전환: D 차폐물 와이프**

```
Slow push-in on the letter, 12 seconds, no cut.
The oil-lamp flame flickers and breathes, its warm light crawling across the
hemp fibers one thread at a time. Dust motes drift diagonally through the beam.
The paper's edge lifts very slightly in an unseen draft.
In the final 2 seconds the dark out-of-focus fabric edge in the extreme
foreground sweeps left-to-right and fills the frame completely -
100% occlusion. Cut on full black fabric.
Camera: 35mm macro, slow dolly in, locked horizon, no shake.
```

---

### H2 · 0:20~0:33 · 미우나이와 딸
**난색 28% · 나가는 전환: E 크로스 디졸브**

```
Locked wide, 13 seconds, almost no camera movement - stillness is the point.
The two silhouettes do not turn. The daughter shifts her weight once.
Wind moves dust across the packed sand in slow sheets, left to right.
Warm lamplight in the distant doorways flickers as figures pass inside.
The sky darkens perceptibly over the shot.
Very slow, almost imperceptible dolly back - the figures get smaller.
Camera: 50mm, locked, 2mm/s pull back. No shake, no drama. Let it hurt.
```

---

### H3 · 0:50~1:02 · 사막폭풍 속 카라반
**난색 40% · 나가는 전환: D 차폐물 와이프**

```
Low ground-level tracking, 12 seconds, camera buried in the sand and moving
backward at walking pace as the caravan strides over and past it.
Hooves land near the lens, kicking sand toward camera. Harness bells swing.
The ochre dust wall behind churns and advances.
In the last 1.5 seconds the nearest camel's dark flank passes directly across
the lens at arm's length and blacks out the entire frame - 100% occlusion.
Cut inside the camel's body.
Camera: 24mm wide, ground level, backward tracking, heavy handheld shake,
motion blur on near hooves.
```

---

### H4 · 1:10~1:24 · 카라반사라이 문이 열린다
**난색 48% · 나가는 전환: C 블랙아웃 통과 (핵심 컷)**

```
14 seconds. The immense timber doors swing inward, revealing the torchlit
courtyard beyond. As they open, the camera begins to move forward - slow at
first, then accelerating - and flies straight through the arch opening.
The dark stone arch mass grows to fill the frame edges, closing in from all
four sides until only a small warm aperture remains at centre, then that
aperture is swallowed as the camera passes into the arch's shadow.
Full black at 14.0s. Cut.
Camera: 28mm, dead-centre symmetrical, forward dolly accelerating from
0 to 3 m/s, no roll, no shake. The door opening and the camera move are one gesture.
```

**이 컷이 채널 문법의 교과서다.** 문이 열리는 동작 자체가 전환 장치가 된다.

---

### H5 · 2:00~2:14 · 설산 X-ray → 융빙수 → 오아시스
**난색 35% · 나가는 전환: B 화이트아웃 통과**

```
14 seconds. Begin on the full mountain cross-section. The glowing cyan
meltwater veins ignite from the summit downward in sequence, branching and
gathering, the light travelling down through the rock over 6 seconds.
The camera descends with the water - a continuous vertical dive down the
mountain's interior - until it emerges at the base and levels out over the
warm oasis, which blooms into light.
In the final 2 seconds the camera pitches up into a bank of high white cloud
and the frame washes to pure white - 100% occlusion. Cut in the cloud.
Camera: vertical descent following the water, then level-out and pitch up.
Continuous, no cut. This is a single unbroken 14-second move.
```

---

### H6 · 3:20~3:34 · 사마르칸트 청록 돔 (직활강)
**난색 50% · 나가는 전환: C 블랙아웃 통과**

```
14 seconds. A true dive. The drone starts high above the turquoise domes and
falls - steeply, almost vertically - toward the central courtyard.
Speed increases through the shot. The domes rush up. Gold light rakes harder
across the glazed tile as the camera closes. Market awnings, then individual
figures, then individual tiles resolve.
The courtyard opening fills the frame in the last 1.5 seconds and the camera
drops through it into the shadowed arcade below - full black. Cut.
Camera: drone direct-descent (직활강), 20 m/s building to 45 m/s,
slight forward pitch, no roll. Gimbal locked. Terrifying speed, perfect stability.
```

**요청하신 "직활강 샷"이 이 컷이다.** 통과 전환과 결합해 컷을 감춘다.

---

### H7 · 3:50~4:10 · 아흐라르의 자산이 점등된다 (최고점)
**난색 57% — 전편 최고 · 나가는 전환: E 크로스 디졸브 · 20초, 가장 긴 컷**

```
20 seconds. The single most spectacular shot of the piece.
The camera rises slowly from below the ground plane, through the buried
irrigation canals, and the network ignites in sequence beneath it:
canal, then fields, then bazaar arcade, then shop rows, then the bathhouse
dome, then the mill wheel turning, then outlying villages far off - each
node blooming warm gold roughly 1.5 seconds apart, twelve ignitions total.
As each lights, a fine luminous gold thread draws itself from that node
toward the centre. The threads converge on one dark courtyard house that
never lights - it stays a black silhouette at the heart of the web.
The camera continues rising until the whole network is visible as one
glowing organism. Hold 2 seconds on the complete web. Dissolve.
Camera: continuous crane up from -5m to +200m over 20 seconds, slight
rotation, no cut. The rise and the ignitions are choreographed to the same clock.
```

**"부자였습니다"라고 말하는 순간 저택 하나 보여주면 실패다.**
자산 네트워크를 한 장면으로 이해시키는 게 이 컷의 임무다. 20초를 쓸 가치가 있다.

---

### H8 · 5:05~5:12 · 카라반 → 컨테이너 match cut
**난색 30%(좌) → 15%(우) · 나가는 전환: A 하드컷 (match cut 자체)**

```
7 seconds, and the cut is invisible.
Start locked on the camel's hoof pressing into ochre sand, dust puffing.
The camera tracks the hoof's motion. At 3.5 seconds, on the exact frame the
hoof lifts, cut to the truck tyre pressing into wet asphalt at the identical
screen position, identical scale, identical motion vector, water spraying in
the same arc. The eye reads one continuous movement across seventeen centuries.
Colour shifts hard on the cut: sand-bronze to steel-teal.
Camera: both halves 24mm at ground level, same tracking speed, same height.
Match the motion vector to within 5 degrees or the cut fails.
```

**3연속 match cut을 여기서 쓴다:** 낙타 발 → 트럭 바퀴 / 카라반사라이 문 → 항만 크레인 / 사막의 붉은 길 → 북극해의 푸른 항로.

---

### H9 · 5:30~5:45 · 북극 지구본 위 컨테이너선
**난색 10% — 전편 최저 · 나가는 전환: B 화이트아웃 통과**

```
15 seconds. Begin in orbit, the polar cap filling the lower frame.
The camera falls toward the planet - a long, slow, silent descent - while the
ship's luminous track draws itself across the ice from Asia toward Europe.
Aurora bands ripple and fade. As the camera drops, the scale collapses:
the whole Arctic, then a sea of ice plates, then a single lead in the ice,
then the ship itself, tiny, its deck lights the only warm pixels in frame.
In the last 2 seconds the camera drops into low ice fog and the frame washes
to white - 100% occlusion. Cut in the fog.
Camera: orbital descent, 400km to 200m over 15 seconds, continuous, no cut.
Absolute stability. Silence. This is the coldest, loneliest frame of the film.
```

---

### H10 · 7:50~8:05 · 부산항 Money X-ray
**난색 15% · 나가는 전환: C 블랙아웃 통과**

```
15 seconds. The port opens up like an anatomy plate.
The camera tracks laterally along the quay while the structure peels into
transparent strata front to back. A luminous cyan-white line traces the cargo
path and lights each layer as it reaches it: ship, then quay crane, then
container stack, then warehouse interior, then rail yard, then the buried
utility trunk. Six ignitions, roughly 2 seconds apart.
Each layer stays lit. By the end the whole port is a single glowing diagram.
In the final 2 seconds the camera passes behind a container stack and the
frame goes black. Cut.
Camera: lateral tracking dolly at 8 m/s, parallax between the transparent
strata doing the heavy lifting. No shake.
```

---

### H11 · 8:15~8:30 · 편지가 돌아온다
**난색 57% — 회복 · 나가는 전환: 페이드 아웃**

```
15 seconds and then black.
The letter lies in full warm gold. Slow push-in, mirroring H1 exactly but
inverted: H1 pushed in through cold blue toward a single ember; this pushes
in through gold. Same lens, same speed, same framing.
Behind, the port bokeh drifts almost imperceptibly.
At 12 seconds the push stops. Hold 3 seconds on stillness. Fade to black.
Camera: 35mm macro, slow dolly in at the identical rate as H1, then hold.
The audience should feel the rhyme without being able to name it.
```

---

## 2. 전환 설계 체크리스트

영상 조립할 때 이것만 지키면 채널 룩이 나온다.

- [ ] 전체 컷 수 약 55개, 중앙값 약 9초
- [ ] 통과 전환(B+C+D) **14~15컷 = 약 25%** — 이것보다 적으면 채널 룩이 아니다
- [ ] 하드컷 약 29컷(52%) — 통과 전환만 쓰면 오히려 이상해진다
- [ ] 난색비율 곡선: 28% → 48% → **57%(H7 정점)** → 10%(H9 최저) → 57%(H11 회복)
- [ ] 얼굴 노출 총합 **25초 미만**. 미우나이 정면 얼굴 0회
- [ ] 그림자는 전부 채도 낮은 청록. 회색 그림자 발견 시 재생성
- [ ] 통과 전환 직전 프레임은 **화면 100% 차폐** 확인 후 컷. 90%는 실패다
- [ ] match cut 3연속(H8 구간)은 모션 벡터 5도 이내로 맞출 것

## 3. 침묵 배치

잉카편 실측 침묵 14회. 8분 30초면 **6~7회**가 비례값이다.

배치 원칙 — 침묵은 질문 직전에 넣는다. 대본의 리듬이
`짧은 문장 → 질문 → 부분답 → 그런데 → 더 큰 질문`이므로,
**"그런데" 바로 앞**이 침묵 자리다.

권장 위치: 0:48(왜였을까요 앞) · 1:38(그런데 두 번째 앞) · 2:33(그런데 물만 앞) ·
4:13(잠깐 앞) · 5:03(그런데 이건 600년 전 앞) · 6:33(왜 길은 짧아졌는데 앞) · 8:13(편지 회수 앞)

## 4. 생성 조건

- 모델: `google/nano-banana-2` (Pollo)
- 비율 `16:9` · 해상도 `1K` · **0크레딧** (Ultra 구독 unlimited 등급)
- 2K는 5크레딧이 붙으므로 쓰지 않았음
- 동시 생성 상한 4개 — 배치로 나눠 제출
