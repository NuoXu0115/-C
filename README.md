# 2027 MCM/ICM Problem C — *On Time, On Paper*
## 美国航班可靠性数据包 · U.S. Flight Reliability Data Package

面向 **2027 年 MCM/ICM C 题**（"准时，只在纸面上：当部分航班永不到达时，哪些机场值得信赖？"）的完整公开数据集，
用于在**旅客视角**下评估、解释并预测航班可靠性——把"准点到达 / 延误到达 / 取消 / 改道 / 字段缺失"分开建模，
并用气象条件解释与预测中断。

> A reproducible public-data package for modelling **passenger-experienced flight reliability**:
> BTS on-time records (45 months), three independent NOAA weather sources, airport/route metadata,
> and daily TSA demand — with audit tables and a full integrity report.

---

## 数据规模

| 项目 | 数值 |
|---|---|
| 航段记录 | **26,227,577** 条（2023-01-01 → 2026-09-30，45 个月） |
| 覆盖机场 | 370 座（其中 20 座为采样机场，配齐气象） |
| 文件总量 | 约 **2.75 GB** / 296 个文件 |
| 数据源 | BTS、NOAA/NCEI、NHC、OurAirports、OpenFlights、TSA |

## 目录结构

```
数据/
├── 00_说明/                 总览、字段字典、机场选择说明、采集脚本、文件清单(SHA256)
├── 01_航班运行_BTS_OTP/     ★核心：BTS 航班准点性能（45 个月）
│   ├── 原始压缩包/          45 个官方月度 zip（未改动，CRC 全部通过）
│   └── 整理数据/            45 个航班级子集(.csv.gz) + 全美机场日度汇总
├── 02_天气_气象/            IEM 逐小时 METAR、NCEI LCD 逐小时、GHCN 逐日、HURDAT2 飓风
├── 03_机场航线_元数据/      机场/跑道/导航台/时区/航空公司 + 派生查找表
├── 04_运力与需求/           TSA 每日安检人数（需求侧）
└── 99_质量检查/             下载日志、清单、审计表、完整性校验报告
```

## 为什么这份数据能支撑整道题

| 题目要求 | 对应数据 |
|---|---|
| 让"消失的航班"计入 | `Cancelled` / `Diverted` / `DivReachedDest` / `ArrTime` 缺失标记——**取消航班在册，但没有到达时间** |
| 看清排名背后的东西 | 逐航班的承运人、计划时刻段（`DepTimeBlk`）、距离、机尾号；机场日度汇总可按月/季/时段重组 |
| 中断前预测 | 航班级特征 + 同时刻机场 METAR + 前序航班状态（`Tail_Number`） |
| 困难的日子 | TSA 日客流峰值、HURDAT2 飓风、GHCN 暴雪、LCD/METAR 低能见度 |
| 评分卡 | 机场日度指标可直接聚合到月/季口径 |

## 由数据实测的关键事实

| 指标 | 全期均值 | 月度最小 | 月度最大 |
|---|---|---|---|
| 取消率 | **1.513%** | 0.145%（2023-11） | **4.712%**（2026-01） |
| 改道率 | 0.268% | 0.097% | 0.538% |
| 到达时间缺失率 | 1.542% | 0.154% | 4.750% |
| 到达延误 ≥15 分钟 | **21.194%** | 13.053% | 28.658% |
| 附有延误原因代码 | 11.532% | 7.443% | 16.712% |

- 全期 **395,923 班取消**、**71,061 班改道**、**403,353 条记录没有到达时间**。
- 取消率与"缺到达时间率"几乎相等（1.51% vs 1.54%）——**缺失本身就是结果**，不是随机噪声。
- 仅 11.5% 的航班有延误原因分解，却有 21.2% 晚点 ≥15 分钟 → 原因字段远不足以解释延误。
- 20 座采样机场的取消率相差 **4.8 倍**（SLC 0.65% ↔ LGA 3.14%）；平均到达延误 11.9 ↔ 22.0 分钟。

## 快速开始

```python
import pandas as pd

# 航班级（已按 20 座采样机场筛选，45 个核心字段）
df = pd.read_csv("数据/01_航班运行_BTS_OTP/整理数据/航班级_20机场_2026-01.csv.gz")
print(df.shape)          # (607577, 45)

# 机场日度（全美 370 座机场）
daily = pd.read_csv("数据/01_航班运行_BTS_OTP/整理数据/机场日度_到达_全美.csv.gz")

# 机场查找表（含流量、取消率、时区、跑道）
apt = pd.read_csv("数据/03_机场航线_元数据/查找表_机场_含流量.csv")
```

旅客视角的行程中断率（建议主指标）：

```python
planned   = len(df)
disrupted = ((df.Cancelled > 0) | (df.ArrDelay >= 15) |
             ((df.Diverted > 0) & (df.DivReachedDest != 1))).sum()
print(disrupted / planned)
```

## 复现

```powershell
cd 数据\00_说明\脚本
python 下载_BTS_OTP.py --workers 10   # 45 个月原始 zip（断点续传）
python 下载_元数据.py                  # 机场/航线/时区
python 生成_气象站点映射.py            # 机场 → NOAA 主站
python 下载_天气.py                    # 20 机场逐小时 METAR
python 下载_LCD.py                     # NCEI LCD 逐小时（2023–2025）
python 下载_GHCN.py                    # GHCN-Daily 逐日
python 下载_TSA.py                     # TSA 每日客流
python 整理_航班数据.py                # 航班级子集 + 机场日度 + 审计
python 生成_查找表.py                  # 机场/承运人查找表
python 校验_数据完整性.py              # CRC、行数、缺失率核对
python 生成_文件清单.py                # 全量 SHA256 与来源 URL
```

## 数据来源与许可

| 数据 | 来源 | 许可 |
|---|---|---|
| 航班准点性能 | U.S. DOT / BTS, TranStats | 美国政府公开数据（public domain） |
| METAR / LCD / GHCN-Daily | NOAA NCEI、Iowa Environmental Mesonet | 美国政府公开数据 |
| 飓风路径 | NOAA NHC, HURDAT2 | 美国政府公开数据 |
| 机场/跑道/导航台 | OurAirports | public domain |
| 时区/航司/航线 | OpenFlights | ODbL |
| 每日客流 | TSA (tsa.gov) | 公开页面 |

数据部分为美国政府公开数据，可自由再分发；`OpenFlights` 为 ODbL，使用时请保留署名。
本仓库中的**脚本与文档**以 MIT 许可发布（见 `LICENSE`）。详见 `NOTICE_数据来源与许可.md`。

## 引用

```bibtex
@misc{mcm2027c_flight_reliability_data,
  title  = {U.S. Flight Reliability Data Package: BTS On-Time Performance + NOAA Weather (2023--2026)},
  year   = {2026},
  note   = {Compiled for the 2027 MCM/ICM Problem C, \emph{On Time, On Paper}},
  url    = {https://github.com/NuoXu0115/-C}
}
```

## 已知限制

1. **取消 ≠ 0 延误**：取消/改道航班无 `ArrDelay`、`ArrTime`；只用已完成航班求平均会高估可靠性。
2. **延误原因不完整**：`CarrierDelay/WeatherDelay/NASDelay/...` 仅对晚点 ≥15 分钟且未取消/未改道的航班填写，且为承运人自报，非独立核实根因。
3. **取消原因**仅 A/B/C/D 四类粗分类。
4. **站点天气 ≠ 航班遭遇的天气**：METAR 为机场地面单点观测，不含航路对流与上游地面停止。
5. **报告口径**：仅"报告承运人"在册（约占美国国内航班 95% 以上）。
6. **2026 年仅到 9 月**，样本外检验缺 Q4 与年末高峰。
7. **时间口径**：BTS 本地时间 / IEM 为 UTC / LCD 为当地时间，不可直接拼接。
8. **LCD 缺 2026 年目录、DEN 不在 LCD 站点**，由 IEM METAR 补齐。

---

<sub>本仓库不含竞赛题目原文（版权归 COMAP 所有）。数据采集时间：2026-11-24。</sub>
