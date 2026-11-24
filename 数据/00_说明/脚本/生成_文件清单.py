# -*- coding: utf-8 -*-
"""生成 数据/00_说明/文件清单.csv：路径、大小、SHA256、来源 URL、状态。"""
import os, json, hashlib, datetime as dt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # = 数据/
DATA = ROOT
DOC = os.path.join(DATA, "00_说明")
QC = os.path.join(DATA, "99_质量检查")
SKIP_EXT = {".md", ".py", ".csv"}  # 清单自身与脚本仍会统计，但不递归记录


def sha256(p, cap=None):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_url_maps():
    m = {}
    for name in ["清单_BTS_OTP.json", "清单_元数据.json", "清单_气象.json",
                 "清单_GHCN.json", "清单_LCD.json"]:
        p = os.path.join(QC, name)
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        for k, v in d.items():
            url = v.get("url")
            if url:
                m[v.get("file") or k] = url
                m[k] = url
    return m


def main():
    urls = load_url_maps()
    rows = []
    for base, dirs, files in os.walk(DATA):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for f in files:
            p = os.path.join(base, f)
            rel = os.path.relpath(p, DATA)
            if rel.startswith("00_说明") and (f.endswith(".py") or f.endswith(".csv")):
                pass
            sz = os.path.getsize(p)
            rows.append(dict(
                path=rel.replace("\\", "/"),
                mb=round(sz / 2**20, 3),
                sha256=sha256(p) if sz < 300 * 2**20 else "(大文件未计算)",
                mtime=dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M"),
                source_url=urls.get(f) or urls.get(os.path.basename(base) + "/" + f) or "",
            ))
    rows.sort(key=lambda r: r["path"])
    out = os.path.join(DOC, "文件清单.csv")
    import csv
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "mb", "sha256", "mtime", "source_url"])
        w.writeheader()
        w.writerows(rows)
    tot = sum(r["mb"] for r in rows)
    print(f"共 {len(rows)} 个文件, {tot/1024:.2f} GB -> {out}")


if __name__ == "__main__":
    main()
