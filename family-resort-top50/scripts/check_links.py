"""데이터와 index.html에 들어 있는 외부 링크의 응답 상태를 확인한다.

호스트별로 요청 간격을 두고, 실패한 링크는 1회만 재시도한다.
결과는 reports/link-report.md에 쓴다. 깨진 링크가 있으면 종료 코드 1.
"""
import json
import re
import time
import urllib.request
from hotel_lib import ROOT, load

UA = "family-resort-top50-linkcheck/1.0 (+https://github.com/geben147-create/-)"


def collect():
    urls = set(re.findall(r'href="(https?://[^"]+)"', (ROOT / "index.html").read_text(encoding="utf-8")))
    hotels, _ = load()
    for h in hotels:
        for ph in h.get("photos", []):
            for k in ("image_source_url", "source_page_url", "license_evidence_url"):
                if ph.get(k):
                    urls.add(ph[k])
        for k in ("official_url", "trip_url"):
            if h.get(k):
                urls.add(h[k])
    return sorted(urls)


def status(url):
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:  # 네트워크 오류
            code = type(e).__name__
        if attempt == 0:
            time.sleep(3)
    return code


def main():
    rows, broken = [], 0
    for url in collect():
        code = status(url)
        ok = isinstance(code, int) and code < 400
        broken += not ok
        rows.append(f"| {'OK' if ok else 'FAIL'} | {code} | {url} |")
        time.sleep(1)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "link-report.md").write_text(
        "# 링크 점검\n\n| 결과 | 상태 | URL |\n|---|---|---|\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"링크 {len(rows)}개 점검, 실패 {broken}개")
    raise SystemExit(1 if broken else 0)


if __name__ == "__main__":
    main()
