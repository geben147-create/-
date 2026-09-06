# 영상 생성 큐 — 이미지 1장 : 영상 1편

원칙: 프롬프트 1개 = 이미지 1장 + **그 이미지로 만든** 영상 1편.
스타일은 장면 성격에 맞춰 섞는다 (v1 다큐 / v5 사진 / v8 유목 인물).

## 무료 조합 (고정)

```
이미지  google/nano-banana-2   16:9  1K    → 0크레딧
영상    minimax/minimax-h3     768p  5초   → 0크레딧
```
**5초가 무료 상한.** 6초부터 과금(30크레딧). 긴 무브는 편집에서 잇는다.
동시 실행 4개는 Pollo 계정의 서버 측 한도 — 늘릴 수 없다.

## 완료 · 진행

| # | 장면 | 스타일 | 이미지 | 영상 무브 | 상태 |
|---|---|---|---|---|---|
| 1 | 등롱 石道 → 문루 | v5 사진 | ✅ | 전진 크레인 + 안개 유동 | 🔄 |
| 2 | 안개 계곡 → 돔 도시 | v5 사진 | ✅ | 상승 크레인 + 돔 점등 | ⏳ |
| 3 | 협곡 다리 저공 질주 | v5 사진 | 🔄 | 전방 질주 + 안개 채찍 | ⏳ |
| 4 | 설산 폭포 뱅킹 활강 | v5 사진 | ⏳ | 뱅킹 하강 | ⏳ |
| 5 | 카라반사라이 문 통과 | v1 다큐 | ✅ | **가속 전진 → 아치 블랙아웃** | 🔄 |
| 6 | 사막폭풍 저공 트래킹 | v1 다큐 | ✅ | 후방 트래킹 + 낙타 차폐 | 🔄 |
| 7 | 편지 극접사 | v1 다큐 | ✅ | 초저속 푸시인 + 램프 흔들림 | ⏳ |
| 8 | 미우나이와 딸 | v1 다큐 | ✅ | 거의 정지 + 초저속 풀백 | ⏳ |
| 9 | 미우나이 + 사막개 | v8 유목 | ✅ | 미풍·눈발·호흡 | 🔄 |
| 10 | 게이트(바로크) | v2 | ✅ | 아치 통과 | ✅ 완료 |

## 영상 무브 설계 원칙 (실측 기반)

1. **나가는 전환을 프롬프트에 넣는다.** 마지막 1~2초에 차폐물이 화면을 100% 덮게 만들고
   거기서 컷한다. 잉카편 실측 통과 전환 25.4%를 재현하는 방법이다.
2. **5초 안에 한 동작만.** 여러 동작을 넣으면 AI가 뭉갠다.
3. **카메라 무브를 문장 끝에 명시한다** — 속도·축·흔들림 유무까지.
   "locked horizon, no shake, no roll" 을 안 쓰면 대부분 흔들린다.
4. **정지 컷도 정지라고 써야 한다.** "almost no camera movement - stillness is the point."
   안 쓰면 모델이 임의로 움직인다.

---

# 격한 무브 문법 — 5초 안에서 최대 속도 뽑기

기존 프롬프트가 너무 얌전했다. AI 영상은 그냥 "카메라가 움직인다"고 쓰면
거의 정지에 가깝게 나온다. 아래 4가지를 지켜야 실제로 확 빨라진다.

## 1. 동작은 딱 하나, 대신 처음부터 끝까지 가속

여러 동작(줌 + 팬 + 틸트)을 섞으면 5초 안에서 형태가 녹는다.
**하나를 골라 첫 프레임부터 마지막까지 계속 가속**시킨다.

```
❌ "camera pushes in while panning right and tilting up"
✅ "camera rockets forward, accelerating violently the whole way"
```

## 2. 대문자와 강한 동사를 쓴다

`EXTREMELY FAST` · `rockets` · `slams toward the lens` · `whips past` ·
`violent acceleration` · `explodes outward` · `at full gallop`

"moves", "travels", "approaches" 같은 중립 동사는 느리게 나온다.

## 3. 종착점을 명시하고, 거기에 차폐물을 둔다

가장 중요하다. 격한 모션은 **후반부에 형태가 무너지기 시작한다.**
무너지기 직전에 화면을 덮어버리면 그 결함이 안 보인다.

```
"...until the dark arch mass fills the entire frame and everything goes black"
"...until the horse's shoulder passes the lens and blacks out the frame"
"...until the dust wall swallows the frame completely"
```

이게 잉카편 실측 **통과 전환 25.4%** 를 그대로 재현하는 방법이기도 하다.
결함 은폐와 채널 문법이 같은 장치로 해결된다.

## 4. 모션 블러와 선명 영역을 나눠 지시한다

```
"heavy motion blur at the frame edges, the centre held sharp"
```

이걸 안 쓰면 전체가 고르게 뭉개지거나, 반대로 전혀 안 흐려져서 속도감이 안 산다.

## 무브 유형별 문장 템플릿

| 무브 | 핵심 문장 |
|---|---|
| **확 줌인 (당기기)** | `EXTREMELY FAST push-in. The subject SLAMS toward the lens, growing from distant to enormous in under two seconds, heavy motion blur at the edges, ending as [occluder] fills the frame.` |
| **돌진 통과** | `The camera ROCKETS forward, accelerating violently from the first frame, [objects] whipping past on both sides as smeared streaks, until [occluder] blacks out the frame.` |
| **직활강** | `A near-vertical DIVE, speed building the whole way, the ground rushing up, torn mist tearing past the lens, ending as the camera drops through [opening] into shadow.` |
| **말 전력질주** | `The horse is at FULL GALLOP, hooves hammering, dust EXPLODING toward the lens, mane and cloak snapping. The camera hurtles backward just ahead of it, barely keeping distance. Heavy motion blur, the horse's head frozen sharp at centre.` |
| **휩 슬라이드** | `A violent WHIP slide left to right, the entire frame smearing into horizontal streaks, resolving hard onto [subject] in the final half second.` |

## 주의 — 속도와 실측 규격의 관계

잉카편 실측 카메라 변위 중앙값은 크지 않다. 원본 채널은 **느린 편**이었다.
따라서 격한 무브는 **실측 재현이 아니라 의도적 연출 변경**이다.

다만 두 가지는 유지된다:
- 통과 전환 비율 25.4% — 오히려 격한 무브가 이걸 **더 쉽게** 만든다
- 난색비율 곡선 — 속도와 무관하게 구간별 광원 지시로 유지

즉 "더 다이나믹하게"는 채널 규격을 깨는 게 아니라
**전환 문법은 그대로 두고 무브 강도만 올리는 것**으로 구현한다.
