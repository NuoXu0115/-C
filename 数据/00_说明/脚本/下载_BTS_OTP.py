# -*- coding: utf-8 -*-
"""
下载 BTS 航空准点性能 (On-Time Performance) 月度原始压缩包。
可断点续传、多线程、校验、生成清单。

用法:  python 下载_BTS_OTP.py [--workers 10]
"""
import os, sys, ssl, time, json, hashlib, threading, argparse, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTDIR = os.path.join(ROOT, "01_航班运行_BTS_OTP", "原始压缩包")
LOGDIR = os.path.join(ROOT, "99_质量检查")
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(LOGDIR, exist_ok=True)

BASE = ("https://transtats.bts.gov/PREZIP/"
        "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{}_{}.zip")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 可用月份：2023-01 .. 2026-09（2026-10 起尚未发布）
TASKS = [(y, m) for y in (2023, 2024, 2025, 2026) for m in range(1, 13)
         if not (y == 2026 and m > 9)]

CTX = ssl.create_default_context()
_lock = threading.Lock()
manifest = {}


def log(msg):
    with _lock:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(os.path.join(LOGDIR, "下载日志_BTS_OTP.txt"), "a", encoding="utf-8") as f:
            f.write(line + "\n")


def sha256(path, cap=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def fetch_one(y, m, retries=6):
    name = f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{y}_{m}.zip"
    dest = os.path.join(OUTDIR, name)
    url = BASE.format(y, m)

    if os.path.exists(dest):
        sz = os.path.getsize(dest)
        # 完整文件大小正常在 24-35 MB 之间
        if sz > 20_000_000:
            manifest[f"{y}-{m:02d}"] = dict(url=url, file=name, bytes=sz,
                                            sha256=sha256(dest), status="cached")
            log(f"跳过(已存在) {y}-{m:02d} {sz/2**20:.1f}MiB")
            return True
        os.remove(dest)

    part = dest + ".part"
    for attempt in range(1, retries + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = dict(UA)
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                total = r.headers.get("Content-Length")
                total = int(total) + have if total else None
                mode = "ab" if have and r.status == 206 else "wb"
                if mode == "wb":
                    have = 0
                with open(part, mode) as f:
                    while True:
                        chunk = r.read(1 << 18)
                        if not chunk:
                            break
                        f.write(chunk)
                        have += len(chunk)
            sz = os.path.getsize(part)
            if total and sz < total:
                raise IOError(f"不完整 {sz}/{total}")
            os.replace(part, dest)
            manifest[f"{y}-{m:02d}"] = dict(url=url, file=name, bytes=sz,
                                            sha256=sha256(dest), status="downloaded")
            log(f"完成 {y}-{m:02d} {sz/2**20:.1f}MiB")
            return True
        except Exception as e:
            wait = min(2 ** attempt, 30)
            log(f"重试 {y}-{m:02d} 第{attempt}次: {type(e).__name__} {str(e)[:80]} 等待{wait}s")
            time.sleep(wait)
    log(f"失败 {y}-{m:02d}")
    return False


def worker(queue, results):
    while True:
        with _lock:
            if not queue:
                return
            y, m = queue.pop(0)
        ok = fetch_one(y, m)
        with _lock:
            results.append((y, m, ok))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()

    open(os.path.join(LOGDIR, "下载日志_BTS_OTP.txt"), "a", encoding="utf-8").close()
    log(f"开始下载 {len(TASKS)} 个月度文件，并发 {a.workers}")
    t0 = time.time()
    queue, results = list(TASKS), []
    threads = [threading.Thread(target=worker, args=(queue, results)) for _ in range(a.workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    dt = time.time() - t0

    man = os.path.join(LOGDIR, "清单_BTS_OTP.json")
    with open(man, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    ok = sum(1 for r in results if r[2])
    tot = sum(v["bytes"] for v in manifest.values())
    log(f"结束: 成功 {ok}/{len(TASKS)}，合计 {tot/2**30:.2f} GiB，用时 {dt/60:.1f} min")


if __name__ == "__main__":
    main()
