# STYLE 2 (문·창문 구조) 생성 스코프

지시일 2026-09-06 · 모델 `google/nano-banana-2` 단독 · 전부 `discountCost: 0`

## 생성 대상 12장

| 코드 | 사업 | 종류 | 비율 |
|---|---|---|---|
| B1-IMAGE | 한국 의료·뷰티 관광 | 히어로 | 16:9 |
| B2-IMAGE | 은퇴 전후 ETF 교육 | 히어로 | 16:9 |
| B3-IMAGE | 금리·경제·주식 리포트 | 히어로 | 16:9 |
| B4-IMAGE | 일일 차트 리포트 | 히어로 | 16:9 |
| B5-IMAGE | 한국어 온라인 교육 | 히어로 | 16:9 |
| B6-IMAGE | 데이터 기반 뷰티·관광 마케팅 | 히어로 | 16:9 |
| B1-CHARACTER | 모모 (크림 고양이) | 캐릭터 | 1:1 |
| B2-CHARACTER | 차곡 (올리브 거북이) | 캐릭터 | 1:1 |
| B3-CHARACTER | 맥로 (네이비 부엉이) | 캐릭터 | 1:1 |
| B4-CHARACTER | 린스 (은회색 스라소니) | 캐릭터 | 1:1 |
| B5-CHARACTER | 한마디 (크림 고양이) | 캐릭터 | 1:1 |
| B6-CHARACTER | 핀 (크림 족제비) | 캐릭터 | 1:1 |

## 제외

- `B1-MOTION` ~ `B6-MOTION` — 영상. 사용자 지시 "영상은 하지마"로 전부 제외.
- STYLE 4 문서의 미제출분 25장 (②~⑥ C02~C06) — 사용자 지시
  "아직 시작안한거는 아예 하지마"로 제출하지 않는다.

## STYLE 4에서 회수만 하는 진행분

이미 제출되어 취소 불가. 전부 0크레딧이라 추가 비용 없음.

| 키 | taskId |
|---|---|
| 4-C01 nano | cmtpp51r43rz3lpeg506p27q4 |
| 1-C02 | cmtpp6ndf3s9wla09ej6qyty3 |
| 1-C03 | cmtppc4vy3szbp398xr3zk6bu |
| 1-C04 | cmtppc9wt3tdz966g99ts7nat |
| 1-C05 | cmtppceqi3t3su51rchb2dkij |
| 1-C06 | cmtppcis83t7og1aocf7ukl39 |

## 무료 보장 절차

1. 제출 전 `pollo_estimate_generation_cost` 로 `discountCost` 확인.
2. `discountCost > 0` 이면 제출하지 않고 사용자에게 묻는다.
3. `activityMode` 가 `unlimited` 가 아니면 같은 절차를 적용한다.
4. `Parallel task limit reached` 거부는 생성이 일어나지 않은 것이므로 차감도 없다.
