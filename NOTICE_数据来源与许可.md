# 数据来源与许可 / Data Sources & Attribution

本仓库中的数据均为**第三方公开数据**，按各自原始许可分发。如果你在论文、报告或产品中使用，
请按下列条目署名。

## 1. 航班运行数据

**U.S. Department of Transportation, Bureau of Transportation Statistics (BTS)**
*Airline On-Time Performance Data*（TranStats）
<https://www.transtats.bts.gov/ONTIME/>

> U.S. Government work — public domain. No restrictions on redistribution.
> 建议引用：Bureau of Transportation Statistics, *Airline On-Time Performance Data*,
> U.S. Department of Transportation, accessed 2026-11-24.

## 2. 气象数据

- **NOAA National Centers for Environmental Information (NCEI)**
  - Integrated Surface Database / METAR 归档（经 Iowa Environmental Mesonet 转发）
  - Local Climatological Data (LCD)
  - GHCN-Daily
  <https://www.ncei.noaa.gov/>
- **Iowa Environmental Mesonet (IEM)**, Iowa State University
  <https://mesonet.agron.iastate.edu/>
- **NOAA National Hurricane Center (NHC)**, HURDAT2 best-track
  <https://www.nhc.noaa.gov/data/hurdat/>

> U.S. Government works — public domain. IEM 作为转发方，仅作数据获取渠道，不主张数据版权。

## 3. 机场与航线元数据

- **OurAirports** — <https://ourairports.com/data/>
  > public domain（其数据页明确声明可自由使用）。
- **OpenFlights** — <https://openflights.org/data.html>
  > 以 **ODbL 1.0**（Open Database License）发布：
  > ① 必须署名；② 若基于其数据构造衍生数据库并公开，需以同等许可共享。
  > 本仓库直接原样分发 `openflights_*.dat` 原始文件，未做修改。

## 4. 需求侧数据

- **Transportation Security Administration (TSA)**, *Passenger Volumes*
  <https://www.tsa.gov/travel/passenger-volumes>
  > 公开网页数据，美国政府作品。

## 5. 本仓库自有内容

- 采集/整理脚本（`数据/00_说明/脚本/*.py`）、文档、派生查找表、审计表：
  **MIT License**（见 `LICENSE`）。
- 派生的聚合表（如 `查找表_机场_含流量.csv`、`机场日度_*.csv.gz`）基于上述公开数据计算，
  随数据一并按原始许可分发；其中涉及 OpenFlights 时区的字段受 ODbL 约束。

## 6. 未包含的内容

- 竞赛题目原文（COMAP 版权所有）未包含在本仓库中。
- 任何价格、票价、旅客个人信息：本数据集**不含**票价与个人层面数据。

---

*采集时间：2026-11-24。每个文件的原始 URL 与 SHA256 见 `数据/00_说明/文件清单.csv`。*
