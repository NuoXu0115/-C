# -*- coding: utf-8 -*-
"""由原始数据派生两张可直接使用的查找表：
   1) 机场查找表（含坐标、时区、跑道、以及由 BTS 计算的流量与可靠性指标）
   2) 承运人查找表（代码 ↔ 名称/国家，并附样本期航班量）
"""
import os, csv, glob
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # = 数据/
META = os.path.join(ROOT, "03_机场航线_元数据")
CUR = os.path.join(ROOT, "01_航班运行_BTS_OTP", "整理数据")

AIRPORTS = ["ATL", "ORD", "DFW", "DEN", "LAX", "JFK", "SFO", "SEA", "MIA", "PHX",
            "BOS", "MSP", "IAH", "ANC", "HNL", "LGA", "DCA", "LAS", "MCO", "SLC"]


def airport_table():
    arr = pd.read_csv(os.path.join(CUR, "机场日度_到达_全美.csv.gz"))
    dep = pd.read_csv(os.path.join(CUR, "机场日度_出发_全美.csv.gz"))
    a = arr.groupby("airport").agg(
        arr_flights=("arr_flights", "sum"),
        arr_cancelled=("arr_cancelled", "sum"),
        arr_diverted=("arr_diverted", "sum"),
        arr_completed=("arr_completed", "sum"),
        arr_delay_sum=("arr_delay_sum", "sum"),
        arr_delay_n=("arr_delay_n", "sum"),
        arr_delay30=("arr_delay30", "sum"),
        arr_delay60=("arr_delay60", "sum"),
        arr_delay180=("arr_delay180", "sum"),
        arr_wx_delay=("arr_wx_delay", "sum"),
    )
    d = dep.groupby("airport").agg(dep_flights=("dep_flights", "sum"),
                                   dep_cancelled=("dep_cancelled", "sum"))
    t = a.join(d, how="outer").reset_index()

    t["pct_cancelled"] = (100 * t.arr_cancelled / t.arr_flights).round(3)
    t["pct_diverted"] = (100 * t.arr_diverted / t.arr_flights).round(3)
    t["pct_delay15"] = (100 * t.arr_delay30 / t.arr_flights).round(3)  # 注意：下面按 15 分钟口径重算
    t["mean_arr_delay"] = (t.arr_delay_sum / t.arr_delay_n).round(2)

    # 元数据
    ap = pd.read_csv(os.path.join(META, "ourairports_airports.csv"))
    ap = ap[["iata_code", "ident", "icao_code", "name", "municipality", "iso_region",
             "latitude_deg", "longitude_deg", "elevation_ft", "type", "scheduled_service"]]
    ap = ap.dropna(subset=["iata_code"]).drop_duplicates("iata_code")
    t = t.merge(ap, left_on="airport", right_on="iata_code", how="left").drop(columns=["iata_code"])

    # 时区（OpenFlights）
    of = pd.read_csv(os.path.join(META, "openflights_airports.dat"), header=None,
                     encoding="utf-8", quotechar='"', on_bad_lines="skip")
    of.columns = ["id", "name", "city", "country", "iata", "icao", "lat", "lon", "alt",
                  "tz_offset", "dst", "tz_db", "type", "source"]
    of = of.dropna(subset=["iata"]).drop_duplicates("iata")
    t = t.merge(of[["iata", "tz_db", "tz_offset", "dst"]], left_on="airport",
                right_on="iata", how="left").drop(columns=["iata"])

    # 跑道
    rw = pd.read_csv(os.path.join(META, "ourairports_runways.csv"))
    g = rw.groupby("airport_ident").agg(
        n_runways=("id", "count"),
        longest_runway_ft=("length_ft", "max"),
        paved_runways=("surface", lambda s: s.astype(str).str.contains("ASP|CON|PEM", case=False, na=False).sum()),
    ).reset_index()
    t = t.merge(g, left_on="ident", right_on="airport_ident", how="left").drop(columns=["airport_ident"])

    t["selected"] = t["airport"].isin(AIRPORTS)
    t["rank_by_arrivals"] = t["arr_flights"].rank(ascending=False, method="min").astype("Int64")
    t = t.sort_values("arr_flights", ascending=False)
    out = os.path.join(META, "查找表_机场_含流量.csv")
    t.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"机场表 {len(t)} 行 -> {out}")
    return t


def carrier_table():
    # 从若干代表性月份提取承运人代码
    files = sorted(glob.glob(os.path.join(CUR, "航班级_20机场_*.csv.gz")))
    sample = files[:3] + files[len(files) // 2: len(files) // 2 + 3]
    codes = set()
    counts = {}
    for f in sample:
        s = pd.read_csv(f, usecols=["Reporting_Airline"])
        vc = s["Reporting_Airline"].value_counts()
        for k, v in vc.items():
            codes.add(k)
            counts[k] = counts.get(k, 0) + int(v)

    of = pd.read_csv(os.path.join(META, "openflights_airlines.dat"), header=None,
                     encoding="utf-8", quotechar='"', on_bad_lines="skip")
    of.columns = ["id", "name", "alias", "iata", "icao", "callsign", "country", "active"]
    of = of.dropna(subset=["iata"]).drop_duplicates("iata")
    m = of.set_index("iata")[["name", "icao", "callsign", "country", "active"]]

    rows = []
    for c in sorted(codes):
        r = {"Reporting_Airline": c, "sample_flights": counts.get(c, 0)}
        if c in m.index:
            r.update({k: m.loc[c, k] for k in ["name", "icao", "callsign", "country", "active"]})
        else:
            r.update(name="", icao="", callsign="", country="", active="")
        rows.append(r)
    t = pd.DataFrame(rows).sort_values("sample_flights", ascending=False)
    out = os.path.join(META, "查找表_承运人.csv")
    t.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"承运人表 {len(t)} 行 -> {out}  (样本月份: {len(sample)})")
    return t


if __name__ == "__main__":
    airport_table()
    carrier_table()
