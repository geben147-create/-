<div align="center">

<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />

  <h1>Built with AI Studio</h2>

  <p>The fastest path from prompt to production with Gemini.</p>

  <a href="https://aistudio.google.com/apps">Start building</a>

</div>

## 🏨 아이와 가기 좋은 물놀이 호텔 200

미국·일본·대만·한국 각 50곳의 자체 추천 목록이에요. 순위와 물놀이 점수(100점 만점)는 자체 평가이고 트립닷컴 공식 순위가 아니에요.

| 경로 | 내용 |
|---|---|
| `family-resort-top50/index.html` | 국가 탭, 검색, 물놀이 점수순 정렬, 시설 필터, 호텔 상세(`#US001` 같은 주소), 사진 10장 갤러리 |
| `family-resort-top50/data/hotels.json` | 원본 데이터. 호텔ID(US001~KR050)는 순위가 바뀌어도 유지 |
| `family-resort-top50/data/settings.json` | 물놀이 점수 가중치 (구글시트 `04_설정` 탭과 같은 값) |
| `family-resort-top50/data/public-hotels.js` | HTML이 읽는 공개용 데이터. 수익·제휴 성과·메모 제외, 사용 허가된 사진만 포함 |
| `family-resort-top50/scripts/` | 검증(`validate_data.py`), 공개 데이터 생성(`build_public.py`), 구글시트 값 생성(`export_sheet.py`), 링크 점검, 갱신 리포트 |
| `.github/workflows/family-resort-checks.yml` | 매일·매주·매월 데이터 검증, 링크 점검, 갱신 필요 목록 생성 |

데이터를 고친 뒤에는 `cd family-resort-top50/scripts && python3 validate_data.py && python3 build_public.py`를 실행하고 커밋하세요.

현재 상태
- 사진: 0장. 사용 허가가 확인된 사진만 공개하고, 사진 출처·허가 증빙은 구글시트 `01_사진원본DB`에서 관리해요.
- 시설 정보: 공식 확인 전. "미확인"은 시설이 없다는 뜻이 아니에요.
- 가격·제휴 링크: 연결 전. 지금 링크는 일반 검색 링크예요.

![미리보기](family-resort-top50/preview.png)
