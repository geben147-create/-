# 제작 규격 최종본

**이 문서가 이전 모든 스타일 문서보다 우선한다.**
(STYLE_GUIDE.md, STYLE_FIXED.md, VIDEO_QUEUE.md 의 상충 내용은 전부 무효)

---

## ⚠️ 정정 — 앞선 "격한 무브" 지시는 폐기한다

세션 중간에 `EXTREMELY FAST` / `ROCKETS` / `SLAMS` / `HURTLES` 문법으로
영상을 뽑았다. **측정 데이터와 정반대였다.** 폐기한다.

측정값: **카메라는 0.1초당 화면폭의 약 0.6% 이동.**
60fps 원본 프레임 기준 약 0.1%. 거의 정지에 가깝다.

---

## 1. 이 포맷의 정체 — 빠른 말 + 느린 그림

| 레이어 | 속도 | 측정 |
|---|---|---|
| 말 (자막 큐) | **매우 빠름** | 1.41초마다 새 문장 · 531큐 · 189단어/분 |
| 그림 (장면) | **매우 느림** | 중앙값 11.9초 — 말보다 8.4배 느리다 |
| 카메라 | **거의 정지** | 0.1초당 화면폭 0.6% |

정보 밀도는 **자막이 담당**하고, 화면은 정보를 주는 대신 **분위기를 유지**한다.
숏폼식으로 컷을 잘게 쪼개면 이 스타일은 오히려 붕괴한다.
19분을 버티게 하는 것은 컷 수가 아니라 **말의 밀도**다.

**실무 함의** — 클립을 많이 만들 필요가 없다.
19분 대본에 필요한 생성 클립은 **100~120개** 수준이고, 상당수는 같은 장소의 각도 변형이다.
8분 30초면 **45~55개**면 충분하다.

---

## 2. 이미지 스타일 (고정 · 확정본)

```
highly detailed painterly cinematic matte painting.
Rich surface texture EVERYWHERE — individually rendered stone blocks and
mortar joints, rope, timber, woven textile, glazed tile with its chipped
weathering, scree, rock strata.
Enormous billowing cumulus clouds with SCULPTED THREE-DIMENSIONAL FORM —
undersides deep in shadow, tops blazing in warm raking light.
Layered ranges receding through deep atmospheric haze into pale bands.
Visible brushwork ONLY in the sky and haze — architecture and terrain carry
PHOTOGRAPHIC levels of detail.
Warm raking light modelling every surface with real shadow depth.
Muted sage-green and slate teal against warm sand / ochre / cream,
small terracotta-red figures the ONLY saturated accents.
High-end animated documentary concept art quality.
No recognizable frontal human face. No text, no lettering, no watermark.
```

### ⚠️ 절대 쓰지 말 것 — 실패했던 표현

| 금지 | 이유 |
|---|---|
| `semi-flat` | 모델이 평면적으로 그린다 |
| `simplified clean forms` | 디테일을 일부러 버린다 |
| `no photoreal detail` | 질감이 통째로 사라진다 |
| `illustrated, not photographed` | 밀도를 낮추는 신호로 작동한다 |

이 네 개를 넣었다가 밋밋한 결과가 나왔다. **정반대로 써야 한다.**

### 핵심 원리 — 붓질은 하늘에만, 지상은 사진급

레퍼런스 룩을 만드는 것은 **밀도의 분리**다.
하늘·안개는 회화적으로 뭉개고, 건축·지형은 돌 하나까지 그린다.
전부 회화로 가면 밋밋해지고, 전부 사진으로 가면 채널 룩이 아니게 된다.

### 인물 규칙

인물은 **항상 작게**, 그리고 **붉은 옷이 화면에서 유일하게 채도 높은 요소**다.
이것이 (1) 얼굴 예산 5% 규칙과 (2) 난색 악센트 35.3% 를 동시에 만족시킨다.
시선을 인물로 끌면서도 얼굴은 안 보이게 하는 장치다.

### 모델

`google/nano-banana-2` · `16:9` · `1K` → **0크레딧**
(더 높은 해상도가 필요하면 `bytedance/seedream-4-5` 가 **4K도 0크레딧**)

## 3. 영상 무브 규격 (측정값)

### 3-1. 속도

**초당 화면폭의 약 6%** (0.1초당 0.6%). 5초 클립이면 총 이동이 화면폭의 **30% 이내**.
"정지 이미지 + 켄번즈"와 "AI 영상 클립"의 경계를 정확히 노린 속도다.

### 3-2. 무브 분포 (확정 장면 70개 실측)

| 무브 | 비율 | 판정 기준 |
|---|---|---|
| **하강 틸트** | **52.9%** | 누적 수직 이동 ≥ 10px (96px 폭 기준) |
| 좌우 팬 | 65.7% (우→좌 34.3 / 좌→우 31.4) | 누적 수평 이동 ≥ 14px |
| 풀백·줌아웃 | 27.1% | 방사 에너지 반경비 < 0.955 |
| 푸시인·줌인 | 21.4% | 방사 에너지 반경비 > 1.05 |
| 상승 틸트 | 17.1% | — |
| 고정에 가까움 | 7.1% | 순수 정지 샷은 사실상 없음 |

### 3-3. 세 가지 원칙

1. **절대로 멈추지 않는다** — 장면의 93%에 움직임이 있다. 다만 극도로 느리다.
2. **한 클립에 무브는 하나** — 회전+줌+상승 동시 요구는 관측되지 않는다.
   복합 무브는 AI 생성에서 목표 상실과 **끝 1초 붕괴**를 일으킨다.
3. **하강 틸트가 기본값** — 절반 이상이 하강 틸트인 이유는 주제어가 "구름 위"이기 때문.
   위에서 아래로 훑으면 관객이 자동으로 높은 곳에 선다.
   **주제가 바뀌면 기본 무브도 바뀐다** — 심해면 하강 돌리, 우주면 풀백.
   실크로드 편은 "길과 거점"이므로 → **수평 팬이 기본, 하강 틸트가 보조.**

### 3-4. 프롬프트 템플릿 (느린 버전)

```
An extremely slow, almost imperceptible [MOVE]. The camera moves at a crawl —
total travel across the whole shot is under a third of the frame width.
[하나의 환경 요소만 미세하게 움직임: 연기, 먼지, 깃발, 물, 불빛].
Nothing else moves. Locked horizon, no shake, no roll, no zoom.
The illustrated painterly rendering is held throughout.
```

`EXTREMELY FAST`, `ROCKETS`, `SLAMS`, `WHIP` 은 **쓰지 않는다.**

### 3-5. 모션 블러는 예외적으로만

잉카편 19분 중 **8초만** 극단적 모션 블러 (13:31~13:38 카하마르카 매복).
그 8초가 영상에서 프레임 간 변화량 최대 구간이다.

**기법** — AI는 복잡한 다수 인물 액션을 못 그린다. 그래서 액션 순간에만 블러를
최대로 올려 **"못 그린 것"을 "빠른 것"으로 바꾼다.**
전체가 선명했기 때문에 그 8초가 속도로 읽힌다. **대비가 만든 효과다.**

8분 30초 편이면 블러 구간은 **3~4초 하나**면 충분하다.

---

## 4. 컷 밀도 — 구간별로 다르게 설계한다

전체 평균을 지키려 하지 말 것. 정보형에서 올리고 정서형에서 내린다.

| 밀도 | 성격 | 회/분 |
|---|---|---|
| 최고 | 제도·구조 설명 (예시 이미지가 많이 필요) | 6.7~6.8 |
| 높음 | 도입 후크 (이탈 방지) | 6.0 |
| 낮음 | 상징 오브젝트 응시 · 결말 | 2.5~2.7 |
| 최저 | 단일 상징물 집중 구간 | 2.2 |

**실크로드 편 배정**

| 대본 구간 | 성격 | 목표 회/분 |
|---|---|---|
| 0:00~0:50 미우나이 (후크) | 도입 | 6.0 |
| 0:50~2:35 카라반사라이·물 연구 | 구조 설명 | 6.5 |
| 2:35~3:20 1,200km 교역로 | 구조 설명 | 6.5 |
| 3:20~5:05 아흐라르 | 인물·자산 | 4.0 |
| 5:05~6:35 부산·북극 | 정보 | 5.5 |
| 6:35~7:50 연결의 조건 | 설명 | 5.0 |
| 7:50~8:15 Money X-ray | 구조 설명 | 6.5 |
| 8:15~8:30 편지 회수 | 결말 | **2.5** |

## 5. 사운드 규격

| 항목 | 측정값 |
|---|---|
| 내레이션 점유율 | 64.0% (36%는 음악·앰비언스만) |
| 덕킹 | 내레이션 구간이 +5.6 dB |
| 스펙트럴 센트로이드 | 내레이션 1,248Hz / 음악만 873Hz — 음악을 저역에 깔아 명료도 확보 |
| 전체 RMS | 중앙값 −18.3 dBFS (p5 −28.8 / p95 −9.4) |
| 대사 사이 정지 | 460회 · 중앙값 0.43초 |
| 3초 이상 침묵 | **14회 — 전부 전환점에 배치** |

### 침묵 배치 원칙 (잉카편 실측 7개 지점)

| 시각 | 길이 | 기능 |
|---|---|---|
| 0:02 | 3.5초 | 오프닝 호흡 |
| 3:02 | 3.9초 | 왕의 등장 직전 정적 |
| 5:00 | 3.2초 | 키푸 공개 직전 |
| 7:45 | **5.9초** | 최장 침묵 — 창고 규모를 눈으로 보게 함 |
| 11:02 | 5.3초 | 전염 확산을 말 없이 |
| 13:38 | 5.4초 | ★ 매복 직후 — 충격을 정적으로 처리 |
| 16:32 | 5.3초 | 정서적 해소 — 감자 공개 직전 |

**규칙** — 침묵은 **공개 직전**과 **충격 직후**에 놓는다.
8분 30초면 비례값 **6~7회**.

실크로드 편 권장 위치:
0:48(왜였을까요 앞) · 1:38(그런데 앞) · 2:33(그런데 물만 앞) · 4:13(잠깐 앞) ·
5:03(600년 전 앞) · **6:33(화물이 부족하다 앞 — 최장 5초)** · 8:13(편지 회수 앞)

---

## 6. 생성 조건 (무료 고정)

```
이미지  google/nano-banana-2   16:9  1K    → 0크레딧
영상    minimax/minimax-h3     768p  5초   → 0크레딧
```
5초 초과 시 과금. 동시 4개는 Pollo 계정 서버 한도.

---

# 7. 컷 체이닝 — `imageTail` 로 컷을 없앤다 (핵심 기법)

## 원리

`minimax-h3` 는 **시작 프레임(`image`)과 종료 프레임(`imageTail`)** 을 동시에 받는다.
A컷을 `image`, B컷을 `imageTail` 에 넣으면 모델이 **A에서 B로 가는 5초**를 만든다.

```
video_1: image=씬A  imageTail=씬B   → A에서 시작해 B에서 끝남
video_2: image=씬B  imageTail=씬C   → B에서 시작해 C에서 끝남
```

`video_1` 의 마지막 프레임과 `video_2` 의 첫 프레임이 **같은 이미지**다.
이어붙이면 컷 지점이 물리적으로 존재하지 않는다. **끊김이 사라진다.**

**비용** — `imageTail` 을 넣어도 768p/5초면 여전히 **0크레딧** (확인함).

## 이 기법이 부수적으로 해결하는 것 두 가지

### (1) "끝 1초 붕괴" 원천 차단

AI 영상의 고질병은 마지막 1초에서 형태가 녹는 것이다.
**종료 프레임이 고정되면 모델이 도착점을 알고 있으므로 녹을 수 없다.**

### (2) 초고속 무브와 고밀도 디테일의 양립

빠른 무브는 디테일을 뭉갠다. 고밀도 매트페인팅과 상극이다.
그런데 **양 끝이 선명한 매트페인팅으로 못박혀 있으면** 중간 구간만 흐려지고
시작·끝은 살아 있다. 모션 블러가 의도된 것처럼 읽힌다.

즉 **속도냐 디테일이냐를 고를 필요가 없다.**

## 실크로드 편 체인 설계

```
둔황 오아시스 → 사막폭풍 → 카라반사라이 → 빙하 융빙수 → 사마르칸트
  → 아흐라르 영지 → [낙타발/트럭바퀴 match cut] → 부산항 → 북극항로 → 편지 회수
```

화살표 하나가 5초 영상 하나. 9개 링크 = **45초가 하나의 연속 이동으로 보인다.**

| # | 시작 → 끝 | 무브 | 대본 |
|---|---|---|---|
| 1 | 둔황 → 사막폭풍 | 마을 이탈 → 봉수대 스쳐 → 먼지벽 진입 | 0:00 → 0:50 |
| 2 | 사막폭풍 → 카라반사라이 | 먼지벽 관통 → 거점 도착 | 0:50 → 1:10 |
| 3 | 카라반사라이 → 사마르칸트 | 평원 저공 돌진 | 1:10 → 3:20 |
| 4 | 빙하 → 사마르칸트 | 빙벽 급강하 → 강 따라 질주 | 2:00 → 3:20 |
| 5 | 사마르칸트 → 아흐라르 영지 | 수로 따라 이탈 → 영지 전경 | 3:20 → 4:15 |
| 6~9 | (미제작) 부산항 · 북극 · 편지 회수 | | 5:05 → 8:30 |

## 프롬프트 템플릿 (체인용)

```
EXTREMELY FAST [MOVE]. From the very first frame the camera ROCKETS
[출발 동작], [중간 통과물] whipping past as smeared streaks, accelerating
the whole way — then [도착 동작] and SLAMS to arrive on [도착 대상].
Heavy motion blur at the frame edges, the centre held sharp.
One single continuous violent acceleration, no cuts, no hesitation,
locked horizon, no roll.
The detailed painterly matte-painting rendering is held throughout —
[재질들] stay solid, no morphing, no warping, no melting of detail.
```

`no morphing, no warping, no melting of detail` 은 **반드시 넣는다.**
이 스타일은 디테일이 생명이라, 돌 줄눈과 타일 문양이 녹으면 전부 무너진다.

## ⚠️ 무브 속도에 대한 기록

§3 은 실측값(0.1초당 화면폭 0.6% — 거의 정지)을 담고 있다.
**§7 의 초고속 체인은 감독의 연출 결정으로 실측값을 의도적으로 벗어난 것이다.**
둘 다 남겨 둔다 — 어느 쪽으로 갈지는 완성본을 보고 정한다.

다만 체이닝 자체는 속도와 무관하게 유효하다.
느린 무브에도 `imageTail` 을 쓰면 컷이 사라진다.
