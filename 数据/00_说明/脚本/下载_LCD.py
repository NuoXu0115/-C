# -*- coding: utf-8 -*-
"""
下载 NOAA NCEI Local Climatological Data (LCD) 逐小时观测。
LCD 与 IEM/METAR 同源（均为 ASOS/AWOS 观测），但来自 NCEI 原始归档、
字段更全、含 REPORT_TYPE 与质量标志，且不受请求频次限制。
文件名：USAF+WBAN（11 位），如 70273026451.csv
"""
import os, ssl, csv, time, json, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "02_天气_气象", "LCD_逐小时")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CTX = ssl.create_default_context()
MAP_CSV = os.path.join(ROOT, "02_天气_气象", "站点表", "机场_ISD气象站映射.csv")
BASE = "https://www.ncei.noaa.gov/data/local-climatological-data/access/{year}/{sid}.csv"
YEARS = [2023, 2024, 2025, 2026]


def fetch(url, timeout=300):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        buf = bytearray()
        while True:
            c = r.read(1 << 18)
            if not c:
                break
            buf += c
        return bytes(buf)


def one(code, sid, year, retries=4):
    dest = os.path.join(OUT, f"{code}_{sid}_{year}.csv")
    if os.path.exists(dest) and os.path.getsize(dest) > 500_000:
        return dest, os.path.getsize(dest), "cached"
    for a in range(retries):
        try:
            d = fetch(BASE.format(year=year, sid=sid))
            if len(d) > 100_000 and d.lstrip().startswith(b'"STATION"'):
                with open(dest, "wb") as f:
                    f.write(d)
                return dest, len(d), "ok"
            return dest, 0, "BADCONTENT"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return dest, 0, "404"
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return dest, 0, "FAIL"


def main():
    rows = list(csv.DictReader(open(MAP_CSV, encoding="utf-8-sig")))
    tasks = []
    for r in rows:
        sid = r["ISD_ID"].replace("-", "")
        for y in YEARS:
            tasks.append((r["IATA"], sid, y))

    man = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(one, c, s, y): (c, s, y) for c, s, y in tasks}
        for fu in as_completed(futs):
            c, s, y = futs[fu]
            p, n, st = fu.result()
            man[os.path.basename(p)] = dict(airport=c, station=s, year=y,
                                            bytes=n, status=st)
            print(f"LCD {st:10s} {n/2**20:6.1f}MB {c}-{y}", flush=True)

    with open(os.path.join(ROOT, "99_质量检查", "清单_LCD.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    ok = sum(1 for v in man.values() if v["bytes"] > 0)
    tot = sum(v["bytes"] for v in man.values())
    print(f"done {ok}/{len(man)}, {tot/2**30:.2f} GiB")
    bad = [k for k, v in man.items() if v["bytes"] == 0]
    if bad:
        print("失败:", bad)


if __name__ == "__main__":
    main()
