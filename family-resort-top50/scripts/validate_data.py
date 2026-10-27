"""hotels.json 구조 검증. 문제가 있으면 종료 코드 1."""
import re
import sys
from collections import Counter
from hotel_lib import load

PREFIX = {"미국": "US", "일본": "JP", "대만": "TW", "한국": "KR"}
FAC_KEYS = ["waterpark_slide", "kids_water", "kids_club_play", "near_attractions", "indoor_pool",
            "outdoor_pool", "water_slide", "kids_pool", "heated_pool", "kids_club"]
LICENSES = {"공개 가능", "미확인", "사용 불가"}


def main():
    hotels, settings = load()
    errors = []
    ids = Counter(h["id"] for h in hotels)
    errors += [f"중복 ID: {i}" for i, n in ids.items() if n > 1]
    per_country = Counter(h["country"] for h in hotels)
    for c in PREFIX:
        if per_country[c] != 50:
            errors.append(f"{c} 호텔 수 {per_country[c]} (50이어야 함)")
    for h in hotels:
        if not re.fullmatch(PREFIX.get(h["country"], "??") + r"\d{3}", h["id"]):
            errors.append(f"{h['id']}: 국가와 ID 접두어 불일치")
        for k in FAC_KEYS:
            if h["facilities"].get(k) not in ("있음", "미확인", "없음"):
                errors.append(f"{h['id']}: facilities.{k} 값 오류")
        if len(h.get("photos", [])) > 10:
            errors.append(f"{h['id']}: 사진 10장 초과")
        for ph in h.get("photos", []):
            if ph.get("license_status") not in LICENSES:
                errors.append(f"{h['id']}/{ph.get('photo_id')}: license_status 값 오류")
    ranks = Counter((h["country"], h["rank"]) for h in hotels)
    errors += [f"중복 순위: {k}" for k, n in ranks.items() if n > 1]
    if sum(settings["weights"].values()) != 100:
        errors.append("점수 가중치 합계가 100이 아님")
    for e in errors:
        print("ERROR", e)
    print(f"검증 완료: 호텔 {len(hotels)}곳, 오류 {len(errors)}건")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
