# -*- coding: utf-8 -*-
"""下载机场/航线/气象站点等参考元数据。"""
import os, ssl, json, time, hashlib, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CTX = ssl.create_default_context()

JOBS = [
    # (url, 目标子目录, 文件名)
    ("https://davidmegginson.github.io/ourairports-data/airports.csv", "03_机场航线_元数据", "ourairports_airports.csv"),
    ("https://davidmegginson.github.io/ourairports-data/runways.csv", "03_机场航线_元数据", "ourairports_runways.csv"),
    ("https://davidmegginson.github.io/ourairports-data/navaids.csv", "03_机场航线_元数据", "ourairports_navaids.csv"),
    ("https://davidmegginson.github.io/ourairports-data/countries.csv", "03_机场航线_元数据", "ourairports_countries.csv"),
    ("https://davidmegginson.github.io/ourairports-data/regions.csv", "03_机场航线_元数据", "ourairports_regions.csv"),
    ("https://davidmegginson.github.io/ourairports-data/airport-frequencies.csv", "03_机场航线_元数据", "ourairports_airport-frequencies.csv"),
    ("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat", "03_机场航线_元数据", "openflights_airports.dat"),
    ("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat", "03_机场航线_元数据", "openflights_airlines.dat"),
    ("https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat", "03_机场航线_元数据", "openflights_routes.dat"),
    ("https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv", "02_天气_气象/站点表", "isd-history.csv"),
    ("https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/isd-lite-format.txt", "02_天气_气象/站点表", "isd-lite-format说明.txt"),
    ("https://www.tsa.gov/travel/passenger-volumes", "04_运力与需求", "tsa_passenger_volumes_raw.html"),
]


def dl(url, sub, name, retries=4):
    outdir = os.path.join(ROOT, sub)
    os.makedirs(outdir, exist_ok=True)
    dest = os.path.join(outdir, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest, os.path.getsize(dest), "cached"
    for a in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                data = r.read()
            with open(dest, "wb") as f:
                f.write(data)
            return dest, len(data), "ok"
        except Exception as e:
            print(f"  retry {a} {name}: {type(e).__name__} {str(e)[:70]}", flush=True)
            time.sleep(2 * a)
    return dest, 0, "FAIL"


def main():
    man = {}
    for url, sub, name in JOBS:
        p, n, st = dl(url, sub, name)
        man[name] = dict(url=url, dir=sub, bytes=n, status=st)
        print(f"{st:8s} {n/1024:9.1f} KB  {sub}/{name}", flush=True)
    with open(os.path.join(ROOT, "99_质量检查", "清单_元数据.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    print("done")


if __name__ == "__main__":
    main()
