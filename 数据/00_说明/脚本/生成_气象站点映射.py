# -*- coding: utf-8 -*-
"""按经纬度最近邻为机场匹配 NOAA ISD 观测站；istoric 表中 END 字段已过时，
因此不按 END 过滤，改为用 ISD-Lite 实际文件是否存在来验证。"""
import os, csv, math, ssl, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
META = os.path.join(ROOT, "03_机场航线_元数据")
ISDH = os.path.join(ROOT, "02_天气_气象", "站点表", "isd-history.csv")
OUT = os.path.join(ROOT, "02_天气_气象", "站点表")
CTX = ssl.create_default_context()

AIRPORTS = ["ATL", "ORD", "DFW", "DEN", "LAX", "JFK", "SFO", "SEA", "MIA", "PHX",
            "BOS", "MSP", "IAH", "ANC", "HNL", "LGA", "DCA", "LAS", "MCO", "SLC"]


def hav(a, b, c, d):
    R = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def exists(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    ap = {}
    with open(os.path.join(META, "ourairports_airports.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["iata_code"] in AIRPORTS and r["type"] in ("large_airport", "medium_airport"):
                ap.setdefault(r["iata_code"], r)

    sts = []
    by_icao = {}
    with open(ISDH, encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                lat, lon = float(r["LAT"]), float(r["LON"])
            except Exception:
                continue
            if not (-90 < lat < 90) or abs(lat) < 0.1:
                continue
            rec = (r["USAF"], r["WBAN"], lat, lon, r["STATION NAME"].strip())
            sts.append(rec)
            ic = (r.get("ICAO") or "").strip().upper()
            if ic and ic not in by_icao:
                by_icao[ic] = rec

    rows = []
    for code in AIRPORTS:
        a = ap.get(code)
        if not a:
            print("缺少机场坐标:", code); continue
        alat, alon = float(a["latitude_deg"]), float(a["longitude_deg"])
        city = (a.get("municipality") or "").upper()
        icao = (a.get("icao_code") or "").strip().upper()

        # 1) 先按 ICAO 精确匹配（KJFK/PANC/PHNL 等），这是最可靠的键
        chosen = None
        if icao and icao in by_icao:
            u, w, la, lo, nm = by_icao[icao]
            if exists(f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/2025/{u}-{w}-2025.gz"):
                chosen = (hav(alat, alon, la, lo), u, w, nm)

        # 2) 退化为最近邻 + 轻度名称加权
        cands = []
        if chosen is None:
            for u, w, la, lo, nm in sts:
                d = hav(alat, alon, la, lo)
                if d > 40:
                    continue
                up = nm.upper()
                s = d + (40 if u == "999999" else 0) + (0 if city and city in up else 25)
                cands.append((s, d, u, w, nm))
            cands.sort()
            for s, d, u, w, nm in cands:
                if exists(f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/2025/{u}-{w}-2025.gz"):
                    chosen = (d, u, w, nm); break
        if chosen:
            d, u, w, nm = chosen
            rows.append(dict(IATA=code, airport_name=a["name"], lat=alat, lon=alon,
                             ISD_ID=f"{u}-{w}", isd_name=nm, distance_km=round(d, 2)))
            print(f"{code}: {u}-{w} {nm[:32]:32s} {d:6.1f} km")
        else:
            print(f"{code}: 无可用 ISD 站")

    if rows:
        dst = os.path.join(OUT, "机场_ISD气象站映射.csv")
        with open(dst, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print("写入", dst, len(rows), "行")


if __name__ == "__main__":
    main()
