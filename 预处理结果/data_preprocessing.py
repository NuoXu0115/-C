# -*- coding: utf-8 -*-
"""
航班数据预处理脚本
作者: 数据科学团队
日期: 2025
功能: 缺失值处理、异常值检测、数据标准化
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
import os
from pathlib import Path

warnings.filterwarnings('ignore')

# 设置中文字体（适配Windows系统）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ============= 路径配置 =============
# 请根据实际情况修改以下路径
BASE_PATH = r"D:\数模\练习3\数据\数据"  # 【替换为本地绝对路径】
INPUT_DIR = os.path.join(BASE_PATH, "01_航班运行_BTS_OTP", "整理数据")
OUTPUT_DIR = r"D:\数模\练习3\预处理结果"  # 【替换为输出路径】

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "figures"), exist_ok=True)

print("=" * 80)
print("航班数据预处理系统")
print("=" * 80)

# ============= 1. 数据加载 =============
print("\n[步骤 1] 加载数据...")

# 读取2023年1月到3月的数据作为示例（完整数据集可加载全部45个月）
data_files = [
    "航班级_20机场_2023-01.csv.gz",
    "航班级_20机场_2023-02.csv.gz",
    "航班级_20机场_2023-03.csv.gz"
]

df_list = []
for file in data_files:
    file_path = os.path.join(INPUT_DIR, file)
    if os.path.exists(file_path):
        df_temp = pd.read_csv(file_path, compression='gzip')
        df_list.append(df_temp)
        print(f"  ✓ 加载 {file}: {len(df_temp)} 行")
    else:
        print(f"  ✗ 文件不存在: {file}")

df_raw = pd.concat(df_list, ignore_index=True)
print(f"\n原始数据总计: {len(df_raw)} 行 × {len(df_raw.columns)} 列")

# 保存原始数据副本用于对比
df_original = df_raw.copy()

# ============= 2. 数据概览 =============
print("\n[步骤 2] 数据概览")
print(f"数据维度: {df_raw.shape}")
print(f"\n数据类型分布:")
print(df_raw.dtypes.value_counts())

# 选择关键数值列进行预处理
numeric_cols = [
    'DepDelay', 'DepDelayMinutes', 'ArrDelay', 'ArrDelayMinutes',
    'TaxiOut', 'AirTime', 'Distance', 'ActualElapsedTime',
    'CarrierDelay', 'WeatherDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay'
]

# 检查列是否存在
numeric_cols = [col for col in numeric_cols if col in df_raw.columns]
print(f"\n待处理的数值列 ({len(numeric_cols)} 列):")
for col in numeric_cols:
    print(f"  - {col}")

# ============= 3. 缺失值分析与处理 =============
print("\n" + "=" * 80)
print("[步骤 3] 缺失值处理")
print("=" * 80)

# 3.1 缺失值统计
missing_stats = pd.DataFrame({
    '列名': df_raw.columns,
    '缺失数量': df_raw.isnull().sum().values,
    '缺失比例(%)': (df_raw.isnull().sum().values / len(df_raw) * 100).round(2)
})
missing_stats = missing_stats[missing_stats['缺失数量'] > 0].sort_values('缺失比例(%)', ascending=False)

print("\n缺失值统计（仅显示有缺失的列）:")
print(missing_stats.to_string(index=False))

# 3.2 缺失值处理策略
print("\n缺失值处理策略:")

# 策略说明
strategies = {
    'DepDelay/ArrDelay': '取消航班导致的缺失，保持NaN（结构性缺失）',
    'TaxiOut/AirTime': '取消航班导致的缺失，保持NaN',
    'CarrierDelay等延误原因': '仅对ArrDel15=1的航班填写，其余用0填充',
    'Distance': '使用中位数填充（该值相对稳定）',
    'ActualElapsedTime': '取消航班缺失，保持NaN'
}

for key, value in strategies.items():
    print(f"  • {key}: {value}")

# 3.3 执行填充
df_processed = df_raw.copy()

# 对延误原因列：非延误航班填充0（表示无该类延误）
delay_reason_cols = ['CarrierDelay', 'WeatherDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay']
for col in delay_reason_cols:
    if col in df_processed.columns:
        # 对于ArrDel15=0或NaN的航班，延误原因填0
        mask = (df_processed['ArrDel15'] == 0) | (df_processed['ArrDel15'].isna())
        df_processed.loc[mask, col] = df_processed.loc[mask, col].fillna(0)
        print(f"  ✓ {col}: 非延误航班填充0")

# Distance使用中位数填充（极少缺失且值稳定）
if 'Distance' in df_processed.columns:
    distance_median = df_processed['Distance'].median()
    df_processed['Distance'].fillna(distance_median, inplace=True)
    print(f"  ✓ Distance: 使用中位数 {distance_median:.1f} 填充")

# ============= 4. 异常值检测与处理 =============
print("\n" + "=" * 80)
print("[步骤 4] 异常值检测与处理")
print("=" * 80)

# 4.1 异常值检测方法说明
print("\n异常值检测方法:")
print("  • 方法1: 3σ原则（适用于近似正态分布的数据）")
print("  • 方法2: IQR箱线图法（适用于偏态分布）")
print("  • 策略: 保留异常值但标记，避免丢失真实极端事件信息")

# 4.2 对关键列进行异常值检测
outlier_cols = ['DepDelay', 'ArrDelay', 'TaxiOut', 'AirTime', 'Distance']
outlier_cols = [col for col in outlier_cols if col in df_processed.columns]

outlier_summary = []

for col in outlier_cols:
    # 跳过缺失值
    data = df_processed[col].dropna()

    if len(data) == 0:
        continue

    # 方法1: 3σ检测
    mean_val = data.mean()
    std_val = data.std()
    lower_3sigma = mean_val - 3 * std_val
    upper_3sigma = mean_val + 3 * std_val
    outliers_3sigma = ((data < lower_3sigma) | (data > upper_3sigma)).sum()

    # 方法2: IQR检测
    Q1 = data.quantile(0.25)
    Q3 = data.quantile(0.75)
    IQR = Q3 - Q1
    lower_iqr = Q1 - 1.5 * IQR
    upper_iqr = Q3 + 1.5 * IQR
    outliers_iqr = ((data < lower_iqr) | (data > upper_iqr)).sum()

    outlier_summary.append({
        '列名': col,
        '均值': f"{mean_val:.2f}",
        '标准差': f"{std_val:.2f}",
        '3σ异常值数': outliers_3sigma,
        '3σ异常值占比(%)': f"{outliers_3sigma/len(data)*100:.2f}",
        'IQR异常值数': outliers_iqr,
        'IQR异常值占比(%)': f"{outliers_iqr/len(data)*100:.2f}"
    })

    # 创建异常值标记列（使用IQR方法，更适合偏态分布）
    df_processed[f'{col}_outlier'] = 0
    mask = (df_processed[col] < lower_iqr) | (df_processed[col] > upper_iqr)
    df_processed.loc[mask, f'{col}_outlier'] = 1

outlier_df = pd.DataFrame(outlier_summary)
print("\n异常值检测结果:")
print(outlier_df.to_string(index=False))

print("\n异常值处理策略:")
print("  • 保留所有异常值（航班延误可能存在真实极端情况）")
print("  • 新增标记列 '{列名}_outlier' 用于后续建模参考")
print("  • 理由: 航班延误、取消属于真实业务场景，不应删除")

# ============= 5. 数据标准化 =============
print("\n" + "=" * 80)
print("[步骤 5] 数据标准化")
print("=" * 80)

print("\n标准化方法选择:")
print("  • Z-score标准化（StandardScaler）: 适用于特征尺度差异大、需要保留分布形状")
print("  • Min-Max标准化: 适用于需要将数据映射到[0,1]区间")
print("  • RobustScaler: 适用于有异常值的数据，基于中位数和IQR")
print("\n本次采用: Z-score标准化（后续建模常用方法）")

# 选择需要标准化的列（排除标记列和分类列）
standardize_cols = [col for col in numeric_cols if col in df_processed.columns and df_processed[col].notna().sum() > 0]

# 创建标准化后的数据
df_standardized = df_processed.copy()

standardize_summary = []
for col in standardize_cols:
    data = df_standardized[col].dropna()
    if len(data) > 0:
        mean_val = data.mean()
        std_val = data.std()

        # 避免除以零
        if std_val > 0:
            df_standardized[f'{col}_scaled'] = (df_standardized[col] - mean_val) / std_val
            standardize_summary.append({
                '列名': col,
                '原始均值': f"{mean_val:.2f}",
                '原始标准差': f"{std_val:.2f}",
                '标准化后列名': f'{col}_scaled'
            })

std_df = pd.DataFrame(standardize_summary)
print("\n标准化统计:")
print(std_df.to_string(index=False))

# ============= 6. 生成对比表 =============
print("\n" + "=" * 80)
print("[步骤 6] 生成处理前后对比")
print("=" * 80)

# 6.1 基本统计对比
comparison_stats = []
for col in numeric_cols[:5]:  # 展示前5列
    if col in df_original.columns:
        comparison_stats.append({
            '列名': col,
            '原始-均值': f"{df_original[col].mean():.2f}",
            '原始-中位数': f"{df_original[col].median():.2f}",
            '原始-缺失数': df_original[col].isna().sum(),
            '处理后-均值': f"{df_processed[col].mean():.2f}",
            '处理后-中位数': f"{df_processed[col].median():.2f}",
            '处理后-缺失数': df_processed[col].isna().sum()
        })

comp_df = pd.DataFrame(comparison_stats)
print("\n数据处理前后对比（部分列）:")
print(comp_df.to_string(index=False))

# ============= 7. 输出处理结果 =============
print("\n" + "=" * 80)
print("[步骤 7] 输出处理结果")
print("=" * 80)

# 7.1 输出前10行和后5行
print("\n处理后数据前10行:")
print(df_processed[numeric_cols[:8]].head(10).to_string())

print("\n处理后数据后5行:")
print(df_processed[numeric_cols[:8]].tail(5).to_string())

# 7.2 保存处理后的数据
output_file = os.path.join(OUTPUT_DIR, "航班数据_预处理完成.csv")
df_processed.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n✓ 预处理数据已保存: {output_file}")

output_file_scaled = os.path.join(OUTPUT_DIR, "航班数据_标准化.csv")
df_standardized.to_csv(output_file_scaled, index=False, encoding='utf-8-sig')
print(f"✓ 标准化数据已保存: {output_file_scaled}")

# ============= 8. 数据可视化 =============
print("\n" + "=" * 80)
print("[步骤 8] 生成可视化图表")
print("=" * 80)

# 8.1 缺失值热力图
fig, ax = plt.subplots(figsize=(14, 8))
missing_matrix = df_raw[numeric_cols].isnull().astype(int)
sns.heatmap(missing_matrix.head(1000), cmap='YlOrRd', cbar_kws={'label': '缺失(1=缺失, 0=存在)'}, ax=ax)
plt.title('缺失值分布热力图（前1000行）', fontsize=16, fontweight='bold')
plt.xlabel('列名', fontsize=12)
plt.ylabel('样本索引', fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
fig_path = os.path.join(OUTPUT_DIR, "figures", "01_缺失值热力图.png")
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✓ 缺失值热力图已保存: {fig_path}")

# 8.2 异常值箱线图对比（处理前后）
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

plot_cols = ['DepDelay', 'ArrDelay', 'TaxiOut', 'AirTime', 'Distance']
plot_cols = [col for col in plot_cols if col in df_processed.columns]

for idx, col in enumerate(plot_cols[:6]):
    if idx < len(axes):
        # 绘制处理前的箱线图
        data_before = df_original[col].dropna()
        data_after = df_processed[col].dropna()

        bp = axes[idx].boxplot([data_before, data_after], showfliers=True, patch_artist=True)
        axes[idx].set_xticklabels(['处理前', '处理后'])
        axes[idx].set_title(f'{col} 异常值对比', fontsize=12, fontweight='bold')
        axes[idx].set_ylabel('数值', fontsize=10)
        axes[idx].grid(True, alpha=0.3)

# 隐藏多余子图
for idx in range(len(plot_cols), len(axes)):
    axes[idx].axis('off')

plt.suptitle('异常值检测箱线图对比', fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
fig_path = os.path.join(OUTPUT_DIR, "figures", "02_异常值箱线图对比.png")
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✓ 异常值箱线图已保存: {fig_path}")

# 8.3 数据分布对比（标准化前后）
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

for idx, col in enumerate(standardize_cols[:6]):
    if idx < len(axes) and f'{col}_scaled' in df_standardized.columns:
        # 原始分布
        data_orig = df_processed[col].dropna()
        data_scaled = df_standardized[f'{col}_scaled'].dropna()

        axes[idx].hist(data_orig, bins=50, alpha=0.6, label='原始数据', color='blue', edgecolor='black')
        ax2 = axes[idx].twinx()
        ax2.hist(data_scaled, bins=50, alpha=0.6, label='标准化后', color='red', edgecolor='black')

        axes[idx].set_xlabel('数值', fontsize=10)
        axes[idx].set_ylabel('频数（原始）', fontsize=10, color='blue')
        ax2.set_ylabel('频数（标准化）', fontsize=10, color='red')
        axes[idx].set_title(f'{col} 标准化对比', fontsize=12, fontweight='bold')
        axes[idx].legend(loc='upper left')
        ax2.legend(loc='upper right')

# 隐藏多余子图
for idx in range(len(standardize_cols[:6]), len(axes)):
    axes[idx].axis('off')

plt.suptitle('数据标准化前后分布对比', fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
fig_path = os.path.join(OUTPUT_DIR, "figures", "03_标准化分布对比.png")
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✓ 标准化分布图已保存: {fig_path}")

# 8.4 相关性热力图
fig, ax = plt.subplots(figsize=(12, 10))
corr_cols = [col for col in numeric_cols if df_processed[col].notna().sum() > 0][:10]
corr_matrix = df_processed[corr_cols].corr()
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0,
            square=True, linewidths=1, cbar_kws={'label': '相关系数'}, ax=ax)
plt.title('特征相关性热力图', fontsize=16, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()
fig_path = os.path.join(OUTPUT_DIR, "figures", "04_相关性热力图.png")
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✓ 相关性热力图已保存: {fig_path}")

# 8.5 散点图矩阵（部分关键变量）
scatter_cols = ['DepDelay', 'ArrDelay', 'Distance', 'AirTime']
scatter_cols = [col for col in scatter_cols if col in df_processed.columns]

if len(scatter_cols) >= 2:
    sample_data = df_processed[scatter_cols].dropna().sample(min(5000, len(df_processed)), random_state=42)

    fig = plt.figure(figsize=(14, 14))
    pd.plotting.scatter_matrix(sample_data, alpha=0.3, figsize=(14, 14), diagonal='hist',
                               color='steelblue', edgecolors='black', linewidth=0.5)
    plt.suptitle('关键变量散点图矩阵（随机抽样5000条）', fontsize=16, fontweight='bold', y=0.995)
    fig_path = os.path.join(OUTPUT_DIR, "figures", "05_散点图矩阵.png")
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ 散点图矩阵已保存: {fig_path}")

# ============= 9. 生成预处理报告 =============
print("\n" + "=" * 80)
print("[步骤 9] 生成预处理报告")
print("=" * 80)

report_path = os.path.join(OUTPUT_DIR, "数据预处理报告.txt")
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("航班数据预处理报告\n")
    f.write("=" * 80 + "\n\n")

    f.write("1. 数据基本信息\n")
    f.write(f"   - 原始数据: {len(df_original)} 行 × {len(df_original.columns)} 列\n")
    f.write(f"   - 处理后数据: {len(df_processed)} 行 × {len(df_processed.columns)} 列\n")
    f.write(f"   - 数据来源: {len(data_files)} 个月份文件\n\n")

    f.write("2. 缺失值处理\n")
    f.write(missing_stats.to_string(index=False))
    f.write("\n\n")

    f.write("3. 异常值检测\n")
    f.write(outlier_df.to_string(index=False))
    f.write("\n\n")

    f.write("4. 数据标准化\n")
    f.write(std_df.to_string(index=False))
    f.write("\n\n")

    f.write("5. 处理策略总结\n")
    f.write("   缺失值: 结构性缺失保留，业务逻辑填充0，距离用中位数\n")
    f.write("   异常值: 保留真实极端值，新增标记列\n")
    f.write("   标准化: Z-score标准化，适用于后续建模\n\n")

    f.write("6. 输出文件\n")
    f.write(f"   - 预处理数据: {output_file}\n")
    f.write(f"   - 标准化数据: {output_file_scaled}\n")
    f.write(f"   - 可视化图表: {os.path.join(OUTPUT_DIR, 'figures')}\n")

print(f"✓ 预处理报告已保存: {report_path}")

print("\n" + "=" * 80)
print("预处理完成！")
print("=" * 80)
print(f"\n所有结果已保存至: {OUTPUT_DIR}")
print("\n文件清单:")
print("  1. 航班数据_预处理完成.csv - 缺失值和异常值处理后的数据")
print("  2. 航班数据_标准化.csv - 包含标准化特征的数据")
print("  3. 数据预处理报告.txt - 详细的处理报告")
print("  4. figures/ - 包含5张可视化图表")
print("\n" + "=" * 80)
