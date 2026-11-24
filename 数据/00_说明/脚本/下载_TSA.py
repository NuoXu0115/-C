# -*- coding: utf-8 -*-
"""抓取 TSA 每日安检通行人数 (2023-2026) 并合并为 CSV。"""
import os, re, csv, ssl, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "04_运力与需求")
CTX = ssl.create_default_context()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

PAGES = {"2026": "https://www.tsa.gov/travel/passenger-volumes",
         "2025": "https://www.tsa.gov/travel/passenger-volumes/2025",
         "2024": "https://www.tsa.gov/travel/passenger-volumes/2024",
         "2023": "https://www.tsa.gov/travel/passenger-volumes/2023"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def parse(h):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) >= 2 and re.match(r"\d{1,2}/\d{1,2}/\d{4}", cells[0]):
            out.append((cells[0], cells[1].replace(",", "")))
    return out


def main():
    rows = []
    for y, url in PAGES.items():
        h = fetch(url)
        p = parse(h)
        print(y, len(p), "rows")
        for d, n in p:
            mm, dd, yy = d.split("/")
            rows.append(dict(date=f"{yy}-{int(mm):02d}-{int(dd):02d}", tsa_throughput=int(n),
                             source_url=url))
    rows.sort(key=lambda r: r["date"])
    # 去重
    seen, uniq = set(), []
    for r in rows:
        if r["date"] in seen:
            continue
        seen.add(r["date"]); uniq.append(r)
    dst = os.path.join(OUT, "TSA_每日安检人数_2023_2026.csv")
    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "tsa_throughput", "source_url"])
        w.writeheader(); w.writerows(uniq)
    print("写入", dst, len(uniq), "行", uniq[0]["date"], "->", uniq[-1]["date"])


if __name__ == "__main__":
    main()
