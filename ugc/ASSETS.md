# 생성 결과 전체 목록

전부 Pollo 계정에 있습니다. 이 컨테이너는 `videocdn.pollo.ai`가 차단이라
링크로만 남깁니다. `compare.html`을 열면 한 화면에 다 보입니다.

## 이미지 9장 · google/nano-banana-2 · 9:16 · 1K · **0 크레딧**

| 컷 | 역할 | 링크 |
|----|------|------|
| S1 | 훅 | https://pollo.ai/v/cmtp82un12ionj89cwqfzz84r |
| S2 | 문제 | https://pollo.ai/v/cmtp85b7d2i6elpeggu3t03u3 |
| S3 | 원인1 | https://pollo.ai/v/cmtp85ee52innu51rrqx3hlhg |
| S4 | 원인2 | https://pollo.ai/v/cmtp85hec2ip9q3ekgtlnse8x |
| S5 | 반전 | https://pollo.ai/v/cmtp85kex2iqzb0hy7xcrlwaq |
| S6 | 해결1 | https://pollo.ai/v/cmtp85noo2ifxn2d4tka8u577 |
| S7 | 해결2 | https://pollo.ai/v/cmtp85qml2i4tine55ojs0m0g |
| S8 | 체크4 | https://pollo.ai/v/cmtp85tfy2hvin2ilf4hlthxs |
| S9 | CTA | https://pollo.ai/v/cmtp82yvo2hz2bpp3tcls46q5 |

## 영상 9컷 · alibaba/wan-v2-2-flash · 5초 · 720p · 컷당 8크레딧

| 컷 | 링크 | 상태 |
|----|------|------|
| S1 | https://pollo.ai/v/cmtp8wl9s2knezjle69wul3ns | 완료 (카나리) |
| S2 | https://pollo.ai/v/cmtp90qs92k8xlpegfj4wwu3o | 완료 |
| S3 | https://pollo.ai/v/cmtp90u552jucn2iltcf3drfa | 완료 |
| S4 | https://pollo.ai/v/cmtp90xrr2ki1p398lhoc3y51 | 완료 |
| S5 | https://pollo.ai/v/cmtp8wrd62kr3ic92qcvovnop | 완료 (카나리) |
| S6 | https://pollo.ai/v/cmtp90zyy2lirtpwk47tplfi8 | 완료 |
| S7 | https://pollo.ai/v/cmtp9167j2kuvmqg8sxrf11fi | 완료 |
| S8 | https://pollo.ai/v/cmtp919pp2jvkn2ilh82hlgof | 완료 |
| S9 | https://pollo.ai/v/cmtp91cua2k7oine5fni98gph | 완료 |

## 모델 비교 (무료 4종, 같은 S1 프롬프트)

| 모델 | 링크 |
|------|------|
| gpt-image-2 | https://pollo.ai/v/cmtp883oz2iulfw7qb527880e |
| nano-banana-2 | https://pollo.ai/v/cmtp82un12ionj89cwqfzz84r |
| seedream-5-lite | https://pollo.ai/v/cmtp8c8kx2j9mtz3fzzknpev0 |
| seedream-4-5 | https://pollo.ai/v/cmtp8cdr72jauj89cdolikeoq |

## 비용 정산

    이미지 9장 + 비교 3장   0 크레딧   (unlimited 모드)
    영상 9컷                72 크레딧  (8 × 9)
    ─────────────────────────────────
    합계                    72 크레딧  (잔액 12,040 중 0.6%)

## 최종 영상 만들기

    # 영상 9개를 clips/S1.mp4 ~ S9.mp4 로 저장  (이미지만 쓰려면 images/S1.png ~)
    python build_video.py

clips/ 에 파일이 있으면 그 컷은 영상으로, 없으면 스틸에 느린 줌으로 처리합니다.
둘을 섞어도 됩니다. 결과: `out/final.mp4` · 1080x1920 · 28.4초 · 30fps.
