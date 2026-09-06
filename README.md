# ai-video-style — 측정 파이프라인 · 편별 비교 · 실크로드편 비주얼 설계

딥 호라이즌 채널의 AI 영상 제작 규격을 **다른 주제에 이식 가능한 형태**로 만드는 작업 저장소.

원본 해부 자료는 [ai-video-style-teardown](https://github.com/geben147-create/ai-video-style-teardown) 에 있다.
이 저장소는 그 위에 얹는 **도구와 다음 편 설계**를 담는다.

---

## 1. 측정 파이프라인 (`pipeline/`)

잉카편 해부에 쓴 측정 코드는 세션 내 임시 실행분이라 남아 있지 않았다.
공개된 원시 덤프와 결과 JSON 만으로 그 계산을 역설계해 실제로 돌아가는 코드로 복원했다.

| 파일 | 역할 | 줄 수 |
|---|---|---|
| `measure.py` | 영상 → raw ffmpeg 덤프 + 11열 10fps 시계열 | 1,235 |
| `derive.py` | 시계열 → 장면 후보·전환·카메라·분당지표·침묵 | 1,498 |
| `compare.py` | 두 편 → 채널 공통 규칙 vs 편별 고유 선택 35지표 | 1,813 |

```bash
python3 pipeline/measure.py <video.mp4> --out episodes/<name>
python3 pipeline/derive.py  --ts episodes/<name>/timeseries/timeseries_10fps.csv \
                            --scenes <verified.json> --out episodes/<name>
python3 pipeline/compare.py --a episodes/inca --b episodes/aztec --out out/compare
```

**실측 재현율** — 잉카편 정답 대조, 검증 에이전트 독립 재측정

```
전환 분류(재계산) 72/72   카메라 cum_x 70/70   perMinute db 20/20
장면 D 72/72              카메라 cum_y 70/70   챕터 3열 각 12/12
장면 dip 72/72            침묵 타임코드 14/14  확정 경계 회수 71/71
전체 1,124/1,170 = 96.1%
```

영상이 있어야만 되는 것(`warm` `V` `zoom` `palette`)은 `null` + `requires_video`
마커로 나간다. 추정치로 채우지 않는다.

자세한 내용은 [`docs/PIPELINE.md`](docs/PIPELINE.md) · [`docs/VALIDATION.md`](docs/VALIDATION.md).

## 2. 편별 비교 프레임워크 (`docs/COMPARISON_FRAMEWORK.md`)

35개 지표, 잉카편 열은 측정값으로 채워져 있고 아즈텍편 열은 비어 있다.
각 행에 **예상 분류(채널규칙 / 편별선택)를 미리 적어** 두었으므로,
아즈텍편을 측정하는 순간 표가 채워지는 게 아니라 **가설이 검정된다.**

n=2 로는 채널 규칙을 확립할 수 없다는 점을 문서 안에 명시했다.
반증은 n=2 에서도 결정적이지만 일치는 그렇지 않다.

## 3. 잔여 오류 감사 (`docs/AUDIT_RESIDUAL.md`)

앞선 6렌즈 감사에서 47건을 고쳤는데, 그것을 통과한 오류가 9건 더 나왔다.

> ⚠️ **`index.html` 을 재생성하면 안 된다.**
> `body1.py:86`, `body2.py:69,100`, `body4.py:40` 에 이미 고친 옛 수치가 남아 있다.
> `assemble.py` 가 이들을 이어붙이므로 재생성하면 오류가 되살아난다. 백포트가 먼저다.

## 4. 실크로드편 비주얼 설계 (`silkroad/`)

측정된 채널 규격을 실제 다음 편에 적용한 첫 사례.

- `VIDEO_PROMPTS.md` — HERO 11컷의 시작 프레임 · 카메라 무브 · 나가는 전환
- `frames.json` · `style_v2.json` — 생성 이력과 무료 모델 지도

적용한 실측 규격: 팔레트(한색 64.7% / 난색 35.3%) · 난색비율 서사 곡선 ·
통과 전환 25.4% · 얼굴 예산 5% 미만 · 장면 길이 분포.

**생성 비용 0크레딧.** 무료 등급 모델만 사용했다 (`silkroad/style_v2.json` 의 `free_model_map` 참조).
