# 최종 확정 스타일 — 이걸로 고정한다

탐색 8종을 거쳐 확정. **이 문서가 이전 STYLE_GUIDE 의 권고보다 우선한다.**

---

## 기본 스타일 (전체의 95%) — 블루아워 부감 사진

```
Elevated aerial view at blue hour. Deep blue-grey dusk sky, the scene below
alive with thousands of small warm amber lights. Thin haze flattening the
distance into pale grey bands. Long-lens elevated view, deep atmospheric
perspective. Photographic, cinematic, high dynamic range, extremely fine
detail. Palette: cool slate blue-grey OVERWHELMINGLY DOMINANT, with
concentrated small warm amber accents and nothing else.
Quiet, vast, monumental.
No recognizable frontal human face. No text, no lettering, no watermark, no logo.
```

### 이 스타일이 맞는 이유 — 실측 근거

잉카편 70,134프레임 k-means 팔레트:

| | 점유율 |
|---|---|
| 한색 (#1B3539 #33555D #5B767B #0B1818 #8C9D9B) | **64.7%** |
| 난색 (#7A5F3E #494636 #B48352 #DFBF8F #392B1A) | **35.3%** |

"한색 지배 + 작고 집중된 난색" 이 채널의 지문이다.
블루아워 부감은 이 구조를 **자연광 조건 하나로** 만들어낸다:
하늘과 대기가 한색을 깔고, 인공조명이 난색 점으로 박힌다.

부수 효과가 셋 더 있다:
- **얼굴 문제 소멸** — 부감이라 인물이 항상 작다. 얼굴 예산 5% 규칙이 저절로 지켜진다
- **AI 취약점 회피** — 손·얼굴·해부학이 화면에 크게 안 나온다
- **난색 곡선 구현이 쉬움** — 불빛 개수만 조절하면 구간별 난색비율이 바뀐다

### 난색비율 곡선 구현 (블루아워 기준)

| 대본 구간 | 목표 난색% | 화면에서의 구현 |
|---|---|---|
| 0:00~1:40 미우나이 | 28% | 불빛 몇 개만. 거의 꺼진 도시 |
| 1:40~3:20 연구·길 | 40~48% | 흐린 낮 또는 이른 블루아워 |
| 3:20~5:05 아흐라르 | **57% (정점)** | 도시 전체 점등. 창문 수천 개 |
| 5:05~7:15 부산·북극 | 10~15% | 강철·얼음. 난색은 크레인 등 몇 개뿐 |
| 7:50~8:30 회수 | 57% | 여명. 난색 회복 |

---

## 보조 스타일 (전체의 5%) — 건축 인포그래픽

**8분 30초 ≈ 55컷 기준 → 약 3컷.** 그 이상 쓰지 않는다.

```
A clean architectural infographic composed as a technical presentation panel.
Behind the overlay, a photographic elevated render at blue hour. Over it, a
precise technical layer in thin pale cyan-white line work: small circular
section vignettes connected by straight leader lines, a dimension line with
tick marks, small EMPTY rectangular label plates left completely blank.
Fine drafting grid ticks in the corners.
Palette: deep blue-grey photographic base, pale cyan-white technical lines,
one restrained warm amber accent.
Absolutely no text, no letters, no words, no numbers - all label plates
must be empty blanks.
```

### 쓸 자리 — 딱 세 곳

| 대본 위치 | 내용 | 왜 여기인가 |
|---|---|---|
| 1:10 | 카라반사라이 거점 구조 | "호텔이면서 창고이면서 물류센터" 나열을 그림 하나로 |
| 5:50 | 북극항로 거리 비교 | 2만km vs 1만3천km — 수치 비교는 도해가 낫다 |
| 7:50 | **부산항 Money X-ray** | 항만→환적→창고→철도→보험 계층 |

### ⚠️ 라벨은 빈 판으로 뽑는다

AI에게 글자를 시키면 깨진 문자가 나온다. **한글은 특히 심하다.**
지시선과 빈 라벨 박스만 생성하고, **텍스트는 편집에서 얹는다.**
프롬프트에 `all label plates must be empty blanks` 를 반드시 넣을 것.

---

## 폐기한 스타일

| | 폐기 사유 |
|---|---|
| v2 고채도 바로크 | 실측 팔레트에서 너무 멂 |
| v3 수채·과슈 | 스케일·속도 표현 약함 |
| v4 인물 회화 단색면 | 배경이 단색이라 전환에 못 씀 |
| v7 3D 카툰 피시아이 | 채널 룩과 무관 |
| v8 유목 인물 회화 | 정면 초상이 얼굴 예산 규칙과 충돌 |
| 순수 도면 보드 | 사진 없이 선만 있으면 채널 룩이 아님 |

## 생성 조건 (무료 고정)

```
이미지  google/nano-banana-2   16:9  1K    → 0크레딧
영상    minimax/minimax-h3     768p  5초   → 0크레딧
```
5초 초과 시 과금. 동시 4개는 계정 한도.
