"""갱신이 필요한 호텔 목록과 데이터 완성 현황을 reports/<kind>-report.md로 만든다.

kind: daily | weekly | monthly
- daily: 사진·시설·가격 미확인 호텔 수 요약과 갱신 필요 목록
- weekly: 사진이 부족한 호텔, 시설 미검증 호텔 목록
- monthly: 사진 라이선스 재검증 대상, Trip.Best 순위 출처 재확인 대상, 제휴 상태 요약
사진 수집·라이선스 판별·가격 조회는 공식 API나 사용 허가가 연결되기 전까지
자동으로 하지 않는다. 이 스크립트는 사람이 처리할 목록만 만든다.
"""
import sys
from collections import Counter
from hotel_lib import ROOT, load, water_score


def main(kind):
    hotels, settings = load()
    lines = [f"# {kind} 리포트", ""]
    no_photo = [h for h in hotels if not h.get("photos")]
    unverified = [h for h in hotels if not h.get("facility_verified_at")]
    public_photos = sum(1 for h in hotels for p in h.get("photos", []) if p.get("license_status") == "공개 가능")
    lines += [f"- 호텔 수: {len(hotels)} ({dict(Counter(h['country'] for h in hotels))})",
              f"- 사진 없는 호텔: {len(no_photo)}",
              f"- 공개 가능한 사진: {public_photos}",
              f"- 시설 미검증 호텔: {len(unverified)}",
              f"- 가격 미확인 호텔: {sum(h['price_status'] == '미확인' for h in hotels)}",
              f"- 제휴 PENDING: {sum(h['affiliate_status'] == 'PENDING' for h in hotels)}", ""]
    if kind in ("daily", "weekly"):
        top = sorted(unverified, key=lambda h: -water_score(h, settings["weights"]))
        lines += ["## 시설 검증 우선 대상 (물놀이 점수 높은 순)", ""]
        lines += [f"- {h['id']} {h['name']} ({water_score(h, settings['weights'])}점)" for h in top[:30]]
    if kind == "weekly":
        lines += ["", "## 사진 후보 탐색 필요", ""]
        lines += [f"- {h['id']} {h['name']} (사진 {len(h.get('photos', []))}장)"
                  for h in hotels if len(h.get("photos", [])) < 10]
    if kind == "monthly":
        lines += ["", "## 사진 라이선스 재검증 대상", ""]
        lines += [f"- {h['id']} {p.get('photo_id')} ({p.get('license_status')})"
                  for h in hotels for p in h.get("photos", [])] or ["- 없음"]
        lines += ["", "## Trip.Best 순위 출처 재확인 대상", ""]
        lines += [f"- {h['id']} {h['name']}" for h in hotels if h["trip_best_listed"]]
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / f"{kind}-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "daily")
