"""구글시트 00_호텔여행_통합MASTER에 넣을 값을 hotels.json에서 만든다.

시트 구성 방식
1. 1행: HEADERS (A~DW, 127열)
2. 2행: template_row(첫 호텔) 전체를 쓰고, 2행을 3~201행에 복사해 수식과 고정값을 채운다.
3. 호텔마다 달라지는 값만 VALUE_BLOCKS 범위에 덮어쓴다. 행은 hotel_id 순서이고,
   갱신할 때는 A열 hotel_id로 행을 찾아 같은 행에 쓴다(중복 행을 만들지 않음).
출력: ../reports/sheet/*.json
"""
import json
from hotel_lib import ROOT, load

ARTIFACT_URL = "https://claude.ai/artifact/R2zdrzxRMrUkEz4xFJp2TX"
SET = "'04_설정'!"

HEADERS = (
    ["호텔ID", "국가", "추천순위(자체)", "호텔명", "대표사진 미리보기", "도시·지역", "물놀이 종합점수(자체 평가)",
     "워터파크·슬라이드", "어린이 물놀이시설", "실내수영장·온수풀", "키즈클럽·놀이시설", "숙박가격",
     "항공권 검색가격", "호텔 예약·제휴 링크", "사진 갤러리 HTML 링크",
     "공식 홈페이지", "트립닷컴 원본 URL", "트립닷컴 공식순위", "공식순위 확인일", "호텔 등급", "이용자 평점",
     "리뷰 수", "추천 연령", "실내 수영장 유무", "야외 수영장 유무", "워터슬라이드 유무", "키즈풀 유무",
     "온수풀 유무", "키즈클럽 유무", "시설 운영기간", "시설 정보 출처"]
    + [f"사진{i:02d}_{k}" for i in range(1, 11) for k in ("URL", "미리보기", "사용상태")]
    + ["숙박 기준일", "숙박 체크아웃일", "객실 인원", "숙박 통화", "숙박 총가격", "가격 확인시각", "출발공항",
       "도착공항", "항공 기준일", "항공 최저 검색가격", "항공 가격 확인시각", "항공 검색 URL", "렌터카 URL",
       "공항 픽업 URL", "가격 상태",
       "추천 여행기간", "추천 계절", "1일차 일정", "2일차 일정", "3일차 일정", "4일차 일정", "5일차 일정",
       "주변 관광지 TOP5", "관광지 입장권 링크", "어린이 추천 체험", "예상 이동 동선", "교통·입장권 주의사항",
       "트립닷컴 호텔 제휴 URL", "트립닷컴 항공 제휴 URL", "트립닷컴 렌터카 제휴 URL", "트립닷컴 패키지 제휴 URL",
       "클룩 제휴 URL", "GetYourGuide 제휴 URL", "기타 제휴 URL", "제휴 승인·발급 상태", "수수료율 및 기준",
       "제휴 클릭 수", "예약 발생 수", "확정 예약 수", "확정 수수료", "제휴 성과 업데이트일",
       "영상 소재 우선점수", "첫 3초 훅", "영상 제목", "30초 대본", "60초 대본", "AI 캐릭터 내레이션",
       "추천 영상 장면 순서", "추천 썸네일 문구", "YouTube Shorts 상태", "인스타 릴스 상태", "틱톡 상태",
       "영상 URL", "영상 조회수", "영상별 제휴 성과 요약",
       "마지막 수집일", "마지막 시설 검증일", "마지막 사진 검증일", "사진 수집 수", "사용 가능한 사진 수",
       "전체 데이터 완성도", "오류·검토 메모",
       "핵심 시설 요약", "테마파크·볼거리 인접", "10~11월 이용 가능성(0~1)", "정보 신뢰도(0~1)"])


def col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


IDX = {col(i + 1): i for i in range(len(HEADERS))}
SEARCH = 'HYPERLINK("https://www.google.com/search?q="&ENCODEURL("site:trip.com "&D2),'


def template_row():
    r = [""] * len(HEADERS)
    put = lambda c, v: r.__setitem__(IDX[c], v)
    put("E", '=IF(AF2="","사진 없음",IMAGE(AF2))')
    put("G", f'=ROUND(IF(H2="있음",{SET}$B$3,0)+IF(I2="있음",{SET}$B$4,0)+IF(J2="있음",{SET}$B$5,0)'
             f'+IF(K2="있음",{SET}$B$6,0)+IF(DU2="있음",{SET}$B$7,0)+DV2*{SET}$B$8+DW2*{SET}$B$9)')
    put("J", '=IF(OR(X2="있음",AB2="있음"),"있음","미확인")')
    put("L", "=" + SEARCH + '"가격 확인")')
    put("M", '=IF(BU2="","해당 없음",HYPERLINK(BU2,"항공권 검색"))')
    put("N", '=IF(CK2<>"",HYPERLINK(CK2,"예약 (제휴)"),' + SEARCH + '"예약 검색 (일반 링크)"))')
    put("O", f'=HYPERLINK("{ARTIFACT_URL}#"&A2,"상세·갤러리")')
    put("P", '=HYPERLINK("https://www.google.com/search?q="&ENCODEURL(D2&" official site"),"공식 사이트 검색")')
    put("AE", "자체 조사(웹검색·일반 공개정보), 공식 확인 전")
    for i in range(10):
        u = col(32 + i * 3)
        r[IDX[u] + 1] = f'=IF({u}2="","",IMAGE({u}2))'
        r[IDX[u] + 2] = "미수집"
    put("BM", '=SWITCH(B2,"미국","USD","일본","JPY","대만","TWD","한국","KRW")')
    put("BU", '=IF(BQ2="","","https://www.google.com/travel/flights?q="&ENCODEURL(BP2&" to "&BQ2))')
    put("BX", "미확인")
    put("BY", '=IF(B2="한국","2박 3일","3박 4일")')
    put("BZ", '=IF(DV2=1,"10~11월 이용 적합","10~11월은 실내 시설 위주")')
    put("CA", "도착·체크인, 호텔 수영장과 키즈 시설 이용")
    put("CB", '=IF(DU2="있음","주변 볼거리 방문: "&DT2,"호텔 물놀이·키즈 시설 이용")')
    put("CC", '=IF(B2="한국","오전 물놀이 후 체크아웃","호텔 시설 재이용 또는 인근 관광")')
    put("CD", '=IF(B2="한국","","체크아웃·출국")')
    put("CI", "확인 전")
    put("CJ", '=IF(DV2<1,"야외 수영장은 계절 운영일 수 있음. 운영기간 확인","시설 운영시간과 예약 필요 여부 확인")')
    put("CR", "PENDING")
    put("CY", f'=ROUND(G2*{SET}$B$25+IF(R2<>"",{SET}$B$26,0))')
    put("CZ", '="아이랑 "&F2&" 간다면 이 호텔 어때요?"')
    put("DA", '=D2&" | "&F2&" 아이와 물놀이 호텔 (물놀이 "&G2&"점)"')
    put("DB", '="[0~3초] "&CZ2&" [3~25초] "&DT2&". [25~30초] 가격과 운영기간은 설명란 링크에서 확인하세요."')
    put("DC", '="[0~3초] "&CZ2&" [3~30초] "&DT2&". [30~50초] 추천 일정: "&CA2&", "&CB2&". [50~60초] 시설 운영기간과 가격은 예약 전에 확인하세요."')
    put("DD", '="안녕! 오늘은 "&F2&"에 있는 "&D2&"를 소개할게. "&DT2&"."')
    put("DE", "호텔 전경 > 메인 수영장 > 키즈 시설 > 주변 볼거리 > 가격 확인 안내 (실제 사진은 허가 확인 후 사용, AI 이미지는 AI 생성 표시)")
    put("DF", '="아이 물놀이 "&G2&"점"')
    for c in ("DG", "DH", "DI"):
        put(c, "미제작")
    put("DM", "'2026-10-26")
    put("DP", "=COUNTA(" + ",".join(f"{col(32 + i * 3)}2" for i in range(10)) + ")")
    put("DQ", '=COUNTIF(AF2:BI2,"공개 가능")')
    put("DR", "=SUMPRODUCT(--(LEN(A2:DS2)>0))/COLUMNS(A2:DS2)")
    put("DS", "시설 미검증, 사진 미수집(작업 환경에서 이미지 사이트 접근 차단), 가격·제휴 미연결")
    return r


def value_blocks(hotels):
    a_k, r_ac, bp_bq, dt_dw = [], [], [], []
    for h in hotels:
        f = h["facilities"]
        a_k.append(["'" + h["id"], h["country"], h["rank"], h["name"], None, h["area"], None,
                    f["waterpark_slide"], f["kids_water"], None, f["kids_club_play"]])
        r_ac.append([h["trip_best_note"], h["trip_best_checked"], None, None, None, None,
                     f["indoor_pool"], f["outdoor_pool"], f["water_slide"], f["kids_pool"],
                     f["heated_pool"], f["kids_club"]])
        bp_bq.append([h["departure_airport"], h["arrival_airport"]])
        dt_dw.append([h["summary"], f["near_attractions"], h["season_fit_oct_nov"], h["info_reliability"]])
    n = len(hotels) + 1
    return {f"A2:K{n}": a_k, f"R2:AC{n}": r_ac, f"BP2:BQ{n}": bp_bq, f"DT2:DW{n}": dt_dw}


def main():
    hotels, _ = load()
    assert len(HEADERS) == 127 and col(len(HEADERS)) == "DW"
    out = ROOT / "reports" / "sheet"
    out.mkdir(parents=True, exist_ok=True)
    (out / "headers.json").write_text(json.dumps([HEADERS], ensure_ascii=False))
    (out / "template_row.json").write_text(json.dumps([template_row()], ensure_ascii=False))
    for rng, vals in value_blocks(hotels).items():
        (out / f"values_{rng.split(':')[0]}.json").write_text(json.dumps(vals, ensure_ascii=False, separators=(",", ":")))
    print("written to", out)


if __name__ == "__main__":
    main()
