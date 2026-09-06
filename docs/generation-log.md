# 생성 로그 — 홈페이지 C01~C06 이미지·영상

## 스코프

- 이미지: 6사업 × C01~C06 = 36 프롬프트, 각 프롬프트를 `google/nano-banana-2` 와
  `bytedance/seedream-4-5` 두 모델로 1장씩 = 72장. 두 모델 모두 discountCost 0.
- 영상: 문서 E항이 C01 한 장면에만, 그리고 ①②③⑥ 네 사업에만 영상을 지시한다.
  ④ 차트 시나리오와 ⑤ 하루한국어는 "C01~C06은 정지 이미지와 실제 웹 요소로 구현한다.
  새 AI 영상을 필수로 만들지 않는다"고 명시되어 있어 영상 대상에서 제외한다.
  C02~C06은 전 사업 공통으로 "새 AI 영상을 생성하지 않는다".

## 확인된 운영 제약 — Pollo 동시 작업 한도

한 번에 6건을 제출하면 전부 `Parallel task limit reached` 로 거부된다.
4건까지는 정상 접수되며 상태 `waiting` 으로 큐에 들어간다.
따라서 배치 크기는 4로 제한하고, 앞 배치가 빠진 뒤 다음 배치를 넣는다.
"병렬로 빠르게"의 실제 상한은 계정 동시 슬롯이지 모델 쪽 제약이 아니다.

## 제출 기록

| 키 | 모델 | taskId |
|---|---|---|
| 1-C01 | seedream-4-5 | cmtpoiy383qtt1407f4y0kc03 |
| 1-C01 | nano-banana-2 | cmtpok5sd3qjxla09cjfrbfvo |
| 2-C01 | seedream-4-5 | cmtpoluud3r022sydya9vmf66 |
| 2-C01 | nano-banana-2 | cmtpom8k23r3a14074oobbbew |
| 3-C01 | seedream-4-5 | cmtponptm3qzap398m8qdyet2 |

## 영상 단계 설정 (전부 0크레딧 검증 완료)

| 모델 | 파라미터 |
|---|---|
| `minimax/minimax-h3` | `resolution: 768P`, `duration: 5` |
| `kling-ai/kling-v3` | `mode: std`, `duration: 5` |
| `alibaba/wan-v3-0-prime` | `resolution: 480p`, `duration: 5` |

사업별 C01 모션 지시 — 전부 카메라 고정, 단일 미세 동작 한 가지만:

- ① TRUSTA K-BEAUTY: 물 표면의 반사광만 아주 작게
- ② 돈의2막: 커튼 끝만 매우 작게
- ③ 머니렌즈: 유리 가장자리 반사광만 미세하게
- ⑥ TRUSTA RADAR: 렌즈 테두리의 반사광만 미세하게
