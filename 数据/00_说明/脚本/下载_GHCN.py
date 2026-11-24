# -*- coding: utf-8 -*-
"""
下载 NOAA GHCN-Daily 逐站日值数据（降水、降雪、最高/最低气温、最大风速等），
覆盖 20 个选定机场的 ASOS 主站。GHCN 站点 ID 规则：USW000 + WBAN。
"""
import os, ssl, csv, time, json, math, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "02_天气_气象", "GHCN_Daily")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CTX = ssl.create_default_context()
MAP_CSV = os.path.join(ROOT, "02_天气_气象", "站点表", "机场_ISD气象站映射.csv")
BASE = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{}.dly"


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        buf = bytearray()
        while True:
            c = r.read(1 << 16)
            if not c:
                break
            buf += c
        return bytes(buf)


def try_station(sid, retries=3):
    dest = os.path.join(OUT, f"{sid}.dly")
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
        return dest, os.path.getsize(dest), "cached"
    for a in range(retries):
        try:
            d = fetch(BASE.format(sid))
            if len(d) > 100_000 and not d.lstrip().startswith(b"<"):
                with open(dest, "wb") as f:
                    f.write(d)
                return dest, len(d), "ok"
            return dest, 0, "NOTFOUND"
        except Exception as e:
            time.sleep(1.5 * (a + 1))
    return dest, 0, "FAIL"


def main():
    # 同时保存站点清单与说明文档
    for name, url in [("ghcnd-stations.txt", "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"),
                      ("ghcnd-version.txt", "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-version.txt"),
                      ("readme.txt", "https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt")]:
        p = os.path.join(OUT, name)
        if os.path.exists(p) and os.path.getsize(p) > 100:
            print("cached", name); continue
        try:
            d = fetch(url, timeout=180)
            with open(p, "wb") as f:
                f.write(d)
            print(f"ok {len(d)/1024:.0f}KB {name}")
        except Exception as e:
            print("FAIL", name, type(e).__name__)

    rows = list(csv.DictReader(open(MAP_CSV, encoding="utf-8-sig")))
    man, todo = {}, []
    for r in rows:
        wban = r["ISD_ID"].split("-")[1]
        sid = "USW000" + wban
        if len(wban) != 5:
            print("异常 WBAN:", r["IATA"], r["ISD_ID"]); continue
        todo.append((r["IATA"], sid))

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(try_station, sid): (code, sid) for code, sid in todo}
        for fu in as_completed(futs):
            code, sid = futs[fu]
            p, n, s = fu.result()
            man[sid] = dict(airport=code, bytes=n, status=s, file=os.path.basename(p))
            print(f"GHCN {s:9s} {n/1024:8.0f}KB {code} {sid}", flush=True)

    with open(os.path.join(ROOT, "99_质量检查", "清单_GHCN.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    ok = sum(1 for v in man.values() if v["bytes"] > 0)
    print(f"done {ok}/{len(man)}")


if __name__ == "__main__":
    main()
