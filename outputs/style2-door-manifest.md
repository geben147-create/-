# STYLE 2 문·창문 구조 — 6사업 히어로 + 뷰티 고양이 3컷

생성일 2026-09-06 · 모델 `google/nano-banana-2` 단독 · 전부 `discountCost: 0`
CDN 접두사 `https://videocdn.pollo.ai/web-cdn/pollo/production/cmf20asu60gslb2k5fhlac2gn/ori/`

## 생성 방식 — 텍스트 프롬프트

업로드된 R01~R12 를 레퍼런스 이미지로 물리지 못했다. 게이트웨이가
`videocdn.pollo.ai:443` 에 403 CONNECT (policy denial) 을 돌려주어 URL 의 그림을
확인할 수 없고, 어느 URL 이 어느 R 번호인지 확정할 방법이 없었다. 잘못 물리면
ETF 히어로에 지하철 패션 사진이 들어가므로 텍스트 프롬프트로 생성했다.

부수 효과로 문서가 경고한 유입 위험(R10 나이키 로고, R12 워터마크,
R04 개장 문구, R07~R09 모델 얼굴)을 함께 피했다.

레퍼런스 conditioning 이 필요하면 사업별로 3~4장씩 나눠 올리면 URL↔R 대응이
확정되므로 그때 정확히 물려 다시 생성한다.

## 히어로 6/6 완성 (16:9, 캐릭터 없음)

| 사업 | 브랜드 | 장면 | 상세 |
|---|---|---|---|
| ① 뷰티 관광 | TRUSTA Voyage | 황금빛 나무 문틀·연분홍 꽃·스파 소품 | https://pollo.ai/v/cmtpqnt9c3xouyqsb90rwdmh3 |
| ② ETF·은퇴 | VORNEL ETF | 네이비 서재·열린 창·황동 스탠드 | https://pollo.ai/v/cmtprf8943yx0bpp34jd1ypth |
| ③ 주식·코인 시장 | VORNEL Market | 버건디 브리핑룸·봉인 봉투·크림 여백 | https://pollo.ai/v/cmtprfdc93ze9gnniff7t8fph |
| ④ 기술적 차트 | VORNEL Signal | 네이비 문틀·수직 반투명 유리 패널 | https://pollo.ai/v/cmtprfh4p3zg6a6j0unl6j1po |
| ⑤ 한국어 학습 | MALRU | 열린 나무문·연분홍 꽃·이어폰 | https://pollo.ai/v/cmtprflua3zzuyqsb2nrz3k31 |
| ⑥ 마케팅 데이터 | TRUSTA Radar | 푸른 반투명 유리 패널·B2B 톤 | https://pollo.ai/v/cmtprjcfx40ectpwkdt9ozxfn |

파일명:

- ① `1788694924783-a7a558c9-4d74-4671-8ebc-74f876b07675.png`
- ② `1788696202221-1a969f8a-d1b5-456d-8d06-3ecd667a68c4.png`
- ③ `1788696208732-221e87fe-5ade-4457-8e60-81cfd243f1c5.png`
- ④ `1788696215100-48d3a5ab-0d98-4d2b-8e9b-b97c0a26a800.png`
- ⑤ `1788696219959-60f82f19-f27d-4153-8bef-04ec40fba1c2.png`
- ⑥ `1788696395675-f4694df1-7e4a-440b-b431-dca6380ad02f.png`

## 뷰티 고양이 3컷 (9:16) — 1/3 완성

사용자 지시 "고양이 캐릭은 뷰티에만 활용" 에 따라 ① TRUSTA Voyage 에만 쓴다.
나머지 다섯 사업은 캐릭터 없음을 유지한다.

고양이 외형은 세 컷 모두 같은 문장으로 고정했다:
통통한 크림빛 흰 고양이, 눈을 감고 편안하게 쉬는 표정, 작고 둥근 귀, 분홍 볼.

| 장면 | 상태 | 상세 |
|---|---|---|
| 서울 — 도심 쇼핑·타워 실루엣·벚꽃 | 완성 | https://pollo.ai/v/cmtpro1jb40a4fw7q41e5hrxj |
| 제주 — 반쯤 열린 나무문·유채밭·바다 | 생성 중 | https://pollo.ai/v/cmtprrx2v40jv703a5wbkwo0h |
| 부산 — 해변 스파·현수교·노을 | 생성 중 | https://pollo.ai/v/cmtprs96c40qelv8h6zq36pc9 |

서울 컷 파일명 `1788696615039-27181b77-5da9-4f78-9405-4e3778d7d75e.png`

## 비용

누적 차감 0. 잔액 11,602 크레딧 변동 없음.
16:9 / 9:16 / 1:1 모두 제출 전 `pollo_estimate_generation_cost` 에서
`discountCost: 0`, `activityMode: unlimited` 확인 후에만 제출했다.
