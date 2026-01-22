#!/usr/bin/env python3
"""
将数据集拆分成两份用于增量训练
支持分层抽样以确保标签分布均衡
"""

import pandas as pd
import argparse
from pathlib import Path
from typing import Tuple
import json


def split_dataset_for_incremental(
    input_path: str,
    output_v1_path: str,
    output_v2_path: str,
    split_ratio: float = 0.5,
    stratify_column: str = None,
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    将数据集拆分成两份

    Args:
        input_path: 输入数据集路径
        output_v1_path: V1版本输出路径
        output_v2_path: V2版本输出路径
        split_ratio: V1版本的数据比例（0-1）
        stratify_column: 分层抽样的列名（如标签列）
        random_seed: 随机种子

    Returns:
        (v1_df, v2_df) 拆分后的两个数据集
    """
    print("=" * 70)
    print("数据集拆分工具 - 增量训练准备")
    print("=" * 70)

    # 1. 读取数据
    print(f"\n📂 读取数据: {input_path}")
    df = pd.read_csv(input_path)
    total_count = len(df)
    print(f"  ✓ 总样本数: {total_count}")

    # 2. 计算拆分数量
    v1_count = int(total_count * split_ratio)
    v2_count = total_count - v1_count

    print(f"\n📊 拆分计划:")
    print(f"  V1版本（初始训练）: {v1_count} 条 ({split_ratio:.1%})")
    print(f"  V2版本（增量训练）: {v2_count} 条 ({1-split_ratio:.1%})")

    # 3. 分层抽样（如果指定了列）
    if stratify_column and stratify_column in df.columns:
        print(f"\n🎯 使用分层抽样（基于: {stratify_column}）")
        v1_df = df.groupby(stratify_column, group_keys=False).apply(
            lambda x: x.sample(n=max(1, int(len(x) * split_ratio)), random_state=random_seed)
        ).reset_index(drop=True)

        # V2是剩余的数据
        v2_df = df[~df.index.isin(v1_df.index)].reset_index(drop=True)

        # 验证标签分布
        print(f"\n标签分布验证:")
        for label in sorted(df[stratify_column].unique()):
            total = len(df[df[stratify_column] == label])
            v1_label = len(v1_df[v1_df[stratify_column] == label])
            v2_label = len(v2_df[v2_df[stratify_column] == label])
            print(f"  {label}: V1={v1_label} ({v1_label/total:.1%}), V2={v2_label} ({v2_label/total:.1%})")
    else:
        print(f"\n🔀 使用随机抽样（随机种子: {random_seed}）")
        v1_df = df.sample(n=v1_count, random_state=random_seed).reset_index(drop=True)
        v2_df = df[~df.index.isin(v1_df.index)].reset_index(drop=True)

    # 4. 打乱顺序
    v1_df = v1_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    v2_df = v2_df.sample(frac=1, random_state=random_seed + 1).reset_index(drop=True)

    # 5. 创建输出目录
    Path(output_v1_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_v2_path).parent.mkdir(parents=True, exist_ok=True)

    # 6. 保存文件
    print(f"\n💾 保存文件:")
    v1_df.to_csv(output_v1_path, index=False)
    print(f"  ✓ V1: {output_v1_path} ({len(v1_df)} 条)")
    v2_df.to_csv(output_v2_path, index=False)
    print(f"  ✓ V2: {output_v2_path} ({len(v2_df)} 条)")

    # 7. 生成统计信息
    stats = {
        "total_samples": total_count,
        "v1_samples": len(v1_df),
        "v2_samples": len(v2_df),
        "split_ratio": split_ratio,
        "stratify_column": stratify_column,
        "random_seed": random_seed,
    }

    # 添加各标签的统计
    if stratify_column and stratify_column in df.columns:
        stats["label_distribution"] = {}
        for label in sorted(df[stratify_column].unique()):
            stats["label_distribution"][label] = {
                "total": int(len(df[df[stratify_column] == label])),
                "v1": int(len(v1_df[v1_df[stratify_column] == label])),
                "v2": int(len(v2_df[v2_df[stratify_column] == label]))
            }

    print("\n" + "=" * 70)
    print("✅ 数据集拆分完成")
    print("=" * 70)

    return v1_df, v2_df, stats


def main():
    parser = argparse.ArgumentParser(
        description='将数据集拆分成两份用于增量训练',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--input', type=str, required=True,
                        help='输入数据集路径')
    parser.add_argument('--output_v1', type=str, required=True,
                        help='V1版本输出路径（初始训练）')
    parser.add_argument('--output_v2', type=str, required=True,
                        help='V2版本输出路径（增量训练）')
    parser.add_argument('--split_ratio', type=float, default=0.5,
                        help='V1版本的数据比例（默认0.5，即各一半）')
    parser.add_argument('--stratify_column', type=str, default='label_level1',
                        help='分层抽样的列名（默认label_level1）')
    parser.add_argument('--random_seed', type=int, default=42,
                        help='随机种子（默认42）')
    parser.add_argument('--stats_output', type=str, default='',
                        help='统计信息输出文件路径（可选）')

    args = parser.parse_args()

    # 执行拆分
    _, _, stats = split_dataset_for_incremental(
        input_path=args.input,
        output_v1_path=args.output_v1,
        output_v2_path=args.output_v2,
        split_ratio=args.split_ratio,
        stratify_column=args.stratify_column,
        random_seed=args.random_seed
    )

    # 保存统计信息
    if args.stats_output:
        with open(args.stats_output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\n📊 统计信息已保存: {args.stats_output}")


if __name__ == '__main__':
    main()
