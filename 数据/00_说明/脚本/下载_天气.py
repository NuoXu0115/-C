# -*- coding: utf-8 -*-
"""多线程下载选定机场逐小时地面气象观测 (IEM ASOS/METAR) 与 NOAA ISD-Lite。"""
import os, ssl, json, time, csv, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "02_天气_气象")
MET = os.path.join(OUT, "METAR_IEM")
ISD = os.path.join(OUT, "ISD_Lite")
for p in (MET, ISD):
    os.makedirs(p, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CTX = ssl.create_default_context()

AIRPORTS = ["ATL", "ORD", "DFW", "DEN", "LAX", "JFK", "SFO", "SEA", "MIA", "PHX",
            "BOS", "MSP", "IAH", "ANC", "HNL", "LGA", "DCA", "LAS", "MCO", "SLC"]
YEARS = [2023, 2024, 2025, 2026]
FIELDS = ("tmpf,dwpf,relh,drct,sknt,gust,vsby,skyc1,skyc2,skyc3,"
          "skyl1,skyl2,skyl3,p01i,wxcodes,ice_accretion_1hr,peak_wind_gust,feel")

MAP_CSV = os.path.join(OUT, "站点表", "机场_ISD气象站映射.csv")

# 阿拉斯加/夏威夷的 ASOS 在 IEM 中以 ICAO 代码建站
STATION_CODE = {"ANC": "PANC", "HNL": "PHNL"}


def load_isd_map():
    with open(MAP_CSV, encoding="utf-8-sig") as f:
        return {r["IATA"]: r["ISD_ID"] for r in csv.DictReader(f)}


ISD_STATIONS = load_isd_map()


def fetch(url, timeout=240):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        buf = bytearray()
        while True:
            c = r.read(1 << 16)
            if not c:
                break
            buf += c
        return bytes(buf)


def metar_url(code, year):
    y2, m2, d2 = (2026, 9, 30) if year == 2026 else (year, 12, 31)
    st = STATION_CODE.get(code, code)
    return ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
            f"station={st}&data={FIELDS}&year1={year}&month1=1&day1=1"
            f"&year2={y2}&month2={m2}&day2={d2}&tz=UTC&format=onlycomma"
            "&latlon=no&missing=M&trace=T&direct=no&report_type=3")


def do_metar(code, year, retries=5):
    dest = os.path.join(MET, f"ASOS_{code}_{year}.csv")
    if os.path.exists(dest) and os.path.getsize(dest) > 20000:
        return dest, os.path.getsize(dest), "cached"
    for a in range(retries):
        try:
            data = fetch(metar_url(code, year))
            if len(data) > 20000 and data.startswith(b"station"):
                with open(dest, "wb") as f:
                    f.write(data)
                return dest, len(data), "ok"
        except Exception as e:
            last = f"{type(e).__name__}"
        time.sleep(1.5 * (a + 1))
    return dest, 0, "FAIL " + locals().get("last", "")


def do_isd(code, year, retries=4):
    st = ISD_STATIONS[code]
    dest = os.path.join(ISD, f"{code}_{st}-{year}.gz")
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        return dest, os.path.getsize(dest), "cached"
    url = f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/{year}/{st}-{year}.gz"
    for a in range(retries):
        try:
            data = fetch(url, timeout=120)
            if len(data) > 500:
                with open(dest, "wb") as f:
                    f.write(data)
                return dest, len(data), "ok"
        except Exception as e:
            last = f"{type(e).__name__}"
        time.sleep(1.5 * (a + 1))
    return dest, 0, "FAIL " + locals().get("last", "")


def main():
    tasks = [("metar", c, y) for c in AIRPORTS for y in YEARS]

    man, t0 = {}, time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {}
        for kind, c, y in tasks:
            fn = do_metar if kind == "metar" else do_isd
            futs[ex.submit(fn, c, y)] = (kind, c, y)
        done = 0
        for fu in as_completed(futs):
            kind, c, y = futs[fu]
            p, n, s = fu.result()
            man[os.path.basename(p)] = dict(kind=kind, airport=c, year=y,
                                            path=os.path.relpath(p, ROOT),
                                            bytes=n, status=s)
            done += 1
            if s != "ok" and s != "cached":
                print(f"[{done}/{len(tasks)}] {s} {kind} {c}-{y}", flush=True)

    with open(os.path.join(ROOT, "99_质量检查", "清单_气象.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    ok = sum(1 for v in man.values() if v["bytes"] > 0)
    tot = sum(v["bytes"] for v in man.values())
    print(f"done: {ok}/{len(man)} files, {tot/2**20:.1f} MiB, {time.time()-t0:.0f}s")
    bad = [k for k, v in man.items() if v["bytes"] == 0]
    if bad:
        print("失败:", bad)


if __name__ == "__main__":
    main()
