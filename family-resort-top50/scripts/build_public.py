"""공개 가능한 필드만 골라 data/public-hotels.js를 만든다.

수익·제휴 성과·내부 메모는 넣지 않는다. 사진은 license_status가
'공개 가능'인 것만 넣는다.
"""
import json
from hotel_lib import DATA, load, water_score

PUBLIC_FIELDS = ["id", "country", "rank", "name", "area", "summary", "flags",
                 "trip_best_listed", "trip_best_note", "facilities", "facility_source",
                 "departure_airport", "arrival_airport", "collected_at",
                 "facility_verified_at", "price_status",
                 "season_fit_oct_nov", "info_reliability"]
PHOTO_FIELDS = ["photo_id", "photo_category", "file_path", "image_source_url",
                "source_page_url", "copyright_owner", "credit_required"]


def main():
    hotels, settings = load()
    out = []
    for h in hotels:
        p = {k: h[k] for k in PUBLIC_FIELDS}
        p["water_score"] = water_score(h, settings["weights"])
        p["photos"] = [{k: ph.get(k) for k in PHOTO_FIELDS}
                       for ph in h.get("photos", []) if ph.get("license_status") == "공개 가능"]
        out.append(p)
    payload = {"season": settings["season"], "score_note": settings["score_note"],
               "weights": settings["weights"], "hotels": out}
    js = "window.HOTEL_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n"
    (DATA / "public-hotels.js").write_text(js, encoding="utf-8")
    print(f"public-hotels.js: {len(out)} hotels, "
          f"{sum(len(p['photos']) for p in out)} public photos")


if __name__ == "__main__":
    main()
