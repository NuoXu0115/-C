# -*- coding: utf-8 -*-
"""
把 BTS 原始月度压缩包整理为分析用数据集（向量化 + category 类型，约 15 秒/月）：
 1) 航班级明细（涉及 20 个选定机场的航班，45 个核心字段）—— 按年月输出 .csv.gz
 2) 全美机场日度汇总（到达 / 出发两个方向）—— 单个文件
 3) 月度审计表（行数、取消、改道、缺报到时间等）
"""
import os, io, json, zipfile
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "01_航班运行_BTS_OTP", "原始压缩包")
CUR = os.path.join(ROOT, "01_航班运行_BTS_OTP", "整理数据")
QC = os.path.join(ROOT, "99_质量检查")
for p in (CUR, QC):
    os.makedirs(p, exist_ok=True)

AIRPORTS = ["ATL", "ORD", "DFW", "DEN", "LAX", "JFK", "SFO", "SEA", "MIA", "PHX",
            "BOS", "MSP", "IAH", "ANC", "HNL", "LGA", "DCA", "LAS", "MCO", "SLC"]

COLS = [
    "FlightDate", "Reporting_Airline", "Tail_Number", "Flight_Number_Reporting_Airline",
    "OriginAirportID", "Origin", "OriginState",
    "DestAirportID", "Dest", "DestState",
    "CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes", "DepDel15", "DepTimeBlk",
    "TaxiOut", "WheelsOff",
    "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes", "ArrDel15", "ArrTimeBlk",
    "Cancelled", "CancellationCode", "Diverted",
    "CRSElapsedTime", "ActualElapsedTime", "AirTime", "Distance",
    "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay",
    "FirstDepTime", "TotalAddGTime", "LongestAddGTime",
    "DivAirportLandings", "DivReachedDest", "DivArrDelay",
    "Div1Airport", "Div1TotalGTime", "Div1LongestGTime",
]

NUM = ["DepDelay", "DepDelayMinutes", "DepDel15", "TaxiOut", "ArrDelay", "ArrDelayMinutes",
       "ArrDel15", "Cancelled", "Diverted", "CRSElapsedTime", "ActualElapsedTime",
       "AirTime", "Distance", "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay",
       "LateAircraftDelay", "TotalAddGTime", "LongestAddGTime", "DivAirportLandings",
       "DivArrDelay", "Div1TotalGTime", "Div1LongestGTime"]
CAT = ["Reporting_Airline", "Origin", "Dest", "OriginState", "DestState",
       "CancellationCode", "Div1Airport", "DepTimeBlk", "ArrTimeBlk", "Tail_Number"]

DTYPES = {c: "float32" for c in NUM}
DTYPES.update({c: "category" for c in CAT})


def process(zp):
    with zipfile.ZipFile(zp) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as fh:
            df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                             usecols=lambda c: c in COLS, dtype=DTYPES, low_memory=False)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")

    canc = (df["Cancelled"].fillna(0) > 0)
    div = (df["Diverted"].fillna(0) > 0)
    arrmiss = df["ArrTime"].isna()

    # ---- 全美机场日度汇总（向量化，避免 lambda 聚合）----
    d = pd.DataFrame({
        "date": df["FlightDate"].values,
        "dest": df["Dest"].values,
        "origin": df["Origin"].values,
        "notcanc": (~canc).astype("int8").values,
        "canc": canc.astype("int8").values,
        "div": div.astype("int8").values,
        "arrmiss": arrmiss.astype("int8").values,
        "arrdelay": df["ArrDelay"].values,
        "arrpos": df["ArrDelay"].clip(lower=0).values,
        "depdelay": df["DepDelay"].values,
        "deppos": df["DepDelay"].clip(lower=0).values,
        "d30": (df["ArrDelay"] >= 30).values.astype("int8"),
        "d60": (df["ArrDelay"] >= 60).values.astype("int8"),
        "d180": (df["ArrDelay"] >= 180).values.astype("int8"),
        "wx": (df["WeatherDelay"].fillna(0) > 0).astype("int8").values,
    })
    arr = d.groupby(["date", "dest"], observed=True, sort=False).agg(
        arr_flights=("canc", "size"),
        arr_cancelled=("canc", "sum"),
        arr_completed=("notcanc", "sum"),
        arr_diverted=("div", "sum"),
        arr_missing_time=("arrmiss", "sum"),
        arr_delay_sum=("arrpos", "sum"),
        arr_delay_n=("arrdelay", "count"),
        arr_delay30=("d30", "sum"),
        arr_delay60=("d60", "sum"),
        arr_delay180=("d180", "sum"),
        arr_wx_delay=("wx", "sum"),
    ).reset_index().rename(columns={"dest": "airport"})

    dep = d.groupby(["date", "origin"], observed=True, sort=False).agg(
        dep_flights=("canc", "size"),
        dep_cancelled=("canc", "sum"),
        dep_diverted=("div", "sum"),
        dep_delay_sum=("deppos", "sum"),
        dep_delay_n=("depdelay", "count"),
    ).reset_index().rename(columns={"origin": "airport"})

    audit = dict(
        rows=int(len(df)),
        cancelled=int(canc.sum()),
        diverted=int(div.sum()),
        arr_time_missing=int(arrmiss.sum()),
        arr_delay_missing=int(df["ArrDelay"].isna().sum()),
        dep_delay_missing=int(df["DepDelay"].isna().sum()),
        cancellation_code_missing=int(df.loc[canc, "CancellationCode"].isna().sum()),
        delay_cause_reported=int((df["CarrierDelay"].fillna(0) > 0).sum()),
        n_airports=int(df["Dest"].nunique()),
        n_carriers=int(df["Reporting_Airline"].nunique()),
        dup_key_rows=int(df.duplicated(
            subset=["FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline",
                    "Origin", "CRSDepTime"]).sum()),
    )
    sub = df[df["Origin"].isin(AIRPORTS) | df["Dest"].isin(AIRPORTS)]
    return sub, arr, dep, audit


def main():
    files = sorted(f for f in os.listdir(RAW) if f.endswith(".zip"))
    print(f"待整理 {len(files)} 个月", flush=True)
    audits, arrs, deps = [], [], []
    for i, f in enumerate(files, 1):
        parts = f.rsplit("_", 2)
        ym = parts[-2] + "-" + parts[-1].replace(".zip", "").zfill(2)
        try:
            sub, arr, dep, audit = process(os.path.join(RAW, f))
        except Exception as e:
            print(f"[{i}/{len(files)}] 失败 {ym}: {type(e).__name__} {e}", flush=True)
            continue
        out = os.path.join(CUR, f"航班级_20机场_{ym}.csv.gz")
        sub.to_csv(out, index=False,
                   compression={"method": "gzip", "compresslevel": 1},
                   float_format="%.3f")
        audit.update(month=ym, subset_rows=int(len(sub)), subset_file=os.path.basename(out),
                     subset_mb=round(os.path.getsize(out) / 2**20, 2))
        audits.append(audit)
        arrs.append(arr); deps.append(dep)
        print(f"[{i}/{len(files)}] {ym}: {audit['rows']:>7d} 行, 子集 {len(sub):>7d}, "
              f"{audit['subset_mb']:.1f}MB, 取消 {audit['cancelled']}", flush=True)

    A = pd.DataFrame(audits)
    A.to_csv(os.path.join(QC, "审计_月度.csv"), index=False, encoding="utf-8-sig")
    AR = pd.concat(arrs, ignore_index=True)
    DP = pd.concat(deps, ignore_index=True)
    AR.to_csv(os.path.join(CUR, "机场日度_到达_全美.csv.gz"), index=False,
              compression={"method": "gzip", "compresslevel": 1})
    DP.to_csv(os.path.join(CUR, "机场日度_出发_全美.csv.gz"), index=False,
              compression={"method": "gzip", "compresslevel": 1})
    print("完成。机场数:", AR["airport"].nunique(), "日期:", AR["date"].min(), AR["date"].max())

    tot = pd.DataFrame(audits)[["rows", "cancelled", "diverted", "arr_time_missing",
                                "arr_delay_missing", "delay_cause_reported",
                                "dup_key_rows"]].sum()
    with open(os.path.join(QC, "审计_总计.json"), "w", encoding="utf-8") as fh:
        json.dump({k: int(v) for k, v in tot.items()}, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
