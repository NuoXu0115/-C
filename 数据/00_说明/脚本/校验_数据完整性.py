# -*- coding: utf-8 -*-
"""
数据完整性校验：核对原始 zip 的 CRC、行数、日期范围，统计关键口径
（取消率、改道率、缺失到达时间、延误原因覆盖），并检查气象/元数据文件。
输出：99_质量检查/校验报告.md 与 校验_明细.csv
"""
import os, io, csv, gzip, json, zipfile, datetime as dt
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "01_航班运行_BTS_OTP", "原始压缩包")
MET = os.path.join(ROOT, "02_天气_气象", "METAR_IEM")
LCD = os.path.join(ROOT, "02_天气_气象", "LCD_逐小时")
GHCN = os.path.join(ROOT, "02_天气_气象", "GHCN_Daily")
QC = os.path.join(ROOT, "99_质量检查")
CUR = os.path.join(ROOT, "01_航班运行_BTS_OTP", "整理数据")

KEY = ["FlightDate", "Reporting_Airline", "Origin", "Dest", "CRSDepTime",
       "Cancelled", "Diverted", "ArrDelay", "ArrTime", "ArrDel15",
       "CarrierDelay", "WeatherDelay", "CancellationCode"]


def check_zips():
    rows = []
    for f in sorted(os.listdir(RAW)):
        if not f.endswith(".zip"):
            continue
        ym = f.rsplit("_", 2)[-2] + "-" + f.rsplit("_", 2)[-1].replace(".zip", "").zfill(2)
        p = os.path.join(RAW, f)
        rec = dict(month=ym, file=f, mb=round(os.path.getsize(p) / 2**20, 2))
        try:
            with zipfile.ZipFile(p) as z:
                bad = z.testzip()
                rec["crc_ok"] = bad is None
                name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
                with z.open(name) as fh:
                    df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                                     usecols=lambda c: c in KEY, low_memory=False)
        except Exception as e:
            rec["crc_ok"] = False
            rec["error"] = f"{type(e).__name__}: {str(e)[:60]}"
            rows.append(rec)
            continue
        n = len(df)
        canc = (df["Cancelled"].fillna(0) > 0)
        div = (df["Diverted"].fillna(0) > 0)
        rec.update(
            rows=n,
            date_min=str(pd.to_datetime(df["FlightDate"]).min().date()),
            date_max=str(pd.to_datetime(df["FlightDate"]).max().date()),
            pct_cancelled=round(100 * canc.mean(), 3),
            pct_diverted=round(100 * div.mean(), 3),
            pct_arr_missing=round(100 * df["ArrTime"].isna().mean(), 3),
            pct_arrdelay_missing=round(100 * df["ArrDelay"].isna().mean(), 3),
            pct_del15=round(100 * (df["ArrDel15"].fillna(0) > 0).mean(), 3),
            pct_cause_reported=round(100 * (df["CarrierDelay"].fillna(0) > 0).mean(), 3),
            n_airports=df["Dest"].nunique(),
            n_carriers=df["Reporting_Airline"].nunique(),
        )
        rows.append(rec)
        print(f"{ym}: {n} 行, 取消 {rec['pct_cancelled']}%, 改道 {rec['pct_diverted']}%, "
              f"缺到达 {rec['pct_arr_missing']}%", flush=True)
    return pd.DataFrame(rows)


def check_weather():
    out = {}
    for d, pat, label in [(MET, ".csv", "METAR(IEM)"), (LCD, ".csv", "LCD(NCEI)"),
                          (GHCN, ".dly", "GHCN-Daily")]:
        if not os.path.isdir(d):
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(pat))
        good, bad = 0, []
        for f in files:
            p = os.path.join(d, f)
            size = os.path.getsize(p)
            if size < 50_000:
                bad.append((f, size)); continue
            good += 1
        out[label] = dict(n=len(files), ok=good, small=bad)
    return out


def main():
    print("=== 校验 BTS 原始压缩包 ===")
    z = check_zips()
    z.to_csv(os.path.join(QC, "校验_明细_月度.csv"), index=False, encoding="utf-8-sig")

    wt = check_weather()

    # 整理后的文件
    cur = []
    if os.path.isdir(CUR):
        for f in sorted(os.listdir(CUR)):
            p = os.path.join(CUR, f)
            cur.append((f, round(os.path.getsize(p) / 2**20, 2)))

    lines = ["# 数据完整性校验报告", "",
             f"生成时间：{dt.datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    lines += ["## 1. BTS 月度原始文件", "",
              f"- 文件数：**{len(z)}**",
              f"- CRC 全部通过：**{bool(z['crc_ok'].all()) if 'crc_ok' in z else 'N/A'}**",
              f"- 总行数：**{int(z['rows'].sum()):,}**",
              f"- 时间覆盖：{z['date_min'].min()} → {z['date_max'].max()}", "",
              "| 指标 | 均值 | 最小 | 最大 |", "|---|---|---|---|"]
    for c in ["pct_cancelled", "pct_diverted", "pct_arr_missing", "pct_arrdelay_missing",
              "pct_del15", "pct_cause_reported"]:
        if c in z:
            lines.append(f"| {c} | {z[c].mean():.3f}% | {z[c].min():.3f}% | {z[c].max():.3f}% |")
    lines += ["", "## 2. 气象数据文件", ""]
    for k, v in wt.items():
        lines.append(f"- **{k}**：{v['n']} 个文件，正常 {v['ok']}，"
                     f"异常 {len(v['small'])}" + (f" → {v['small'][:5]}" if v['small'] else ""))
    lines += ["", "## 3. 整理后数据集", ""]
    for f, mb in cur:
        lines.append(f"- `{f}` — {mb} MB")
    if os.path.exists(os.path.join(QC, "审计_总计.json")):
        tot = json.load(open(os.path.join(QC, "审计_总计.json"), encoding="utf-8"))
        lines += ["", "## 4. 全期合计", ""]
        for k, v in tot.items():
            lines.append(f"- `{k}` = {v:,}")

    p = os.path.join(QC, "校验报告.md")
    open(p, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:20]))
    print("\n写入", p)


if __name__ == "__main__":
    main()
