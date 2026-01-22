#!/usr/bin/env python3
"""
增量训练数据准备脚本
支持旧数据采样、新旧数据合并等策略
"""

import pandas as pd
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


def prepare_incremental_data(
    new_data_path: str,
    old_data_path: Optional[str],
    output_path: str,
    strategy: str = "sample",  # sample | merge | new_only
    sample_ratio: float = 0.3,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    准备增量训练数据

    Args:
        new_data_path: 新数据路径
        old_data_path: 旧数据路径（可选）
        output_path: 输出数据路径
        strategy: 数据合并策略
            - sample: 采样旧数据 + 新数据
            - merge: 全部旧数据 + 新数据
            - new_only: 仅新数据
        sample_ratio: 旧数据采样比例 (0-1)
        random_seed: 随机种子

    Returns:
        数据统计信息字典
    """
    print("=" * 70)
    print("增量训练数据准备")
    print("=" * 70)

    # 1. 读取新数据
    print(f"\n📂 读取新数据: {new_data_path}")
    new_df = pd.read_csv(new_data_path)
    new_count = len(new_df)
    print(f"  ✓ 新数据样本数: {new_count}")

    # 2. 根据策略处理旧数据
    if strategy == "new_only":
        print(f"\n📋 策略: 仅使用新数据 (new_only)")
        combined_df = new_df
        old_count_used = 0

    elif old_data_path:
        print(f"\n📂 读取旧数据: {old_data_path}")
        old_df = pd.read_csv(old_data_path)
        old_total_count = len(old_df)
        print(f"  ✓ 旧数据样本数: {old_total_count}")

        if strategy == "merge":
            print(f"\n📋 策略: 合并全部旧数据 (merge)")
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
            old_count_used = old_total_count

        elif strategy == "sample":
            print(f"\n📋 策略: 采样旧数据 (sample)")
            print(f"  采样比例: {sample_ratio:.1%}")

            sample_size = max(1, int(old_total_count * sample_ratio))
            print(f"  采样数量: {sample_size} / {old_total_count}")

            sampled_old = old_df.sample(n=sample_size, random_state=random_seed)
            combined_df = pd.concat([sampled_old, new_df], ignore_index=True)
            old_count_used = sample_size
    else:
        print(f"\n⚠️  未提供旧数据路径，仅使用新数据")
        combined_df = new_df
        old_count_used = 0

    # 3. 打乱数据（避免新旧数据的顺序影响训练）
    print(f"\n🔀 打乱数据顺序 (随机种子: {random_seed})")
    combined_df = combined_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)

    # 4. 保存到输出路径
    print(f"\n💾 保存准备好的数据: {output_path}")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    # 5. 返回数据统计信息
    stats = {
        "total_samples": len(combined_df),
        "new_samples": new_count,
        "old_samples_used": old_count_used,
        "old_samples_available": len(pd.read_csv(old_data_path)) if old_data_path else 0,
        "strategy": strategy,
        "sample_ratio": sample_ratio if strategy == "sample" else None,
        "random_seed": random_seed
    }

    print("\n" + "=" * 70)
    print("✅ 数据准备完成")
    print("=" * 70)
    print(f"总样本数: {stats['total_samples']}")
    print(f"  - 新数据: {stats['new_samples']}")
    print(f"  - 旧数据: {stats['old_samples_used']}", end="")
    if stats['old_samples_available'] > 0:
        print(f" (可用: {stats['old_samples_available']})")
    else:
        print()
    print(f"策略: {stats['strategy']}")
    if stats['sample_ratio']:
        print(f"采样比例: {stats['sample_ratio']:.1%}")
    print()

    return stats


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='准备增量训练数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:

  # 仅使用新数据
  python prepare_incremental_data.py \\
      --new_data datasets/new/train.csv \\
      --output /tmp/prepared_train.csv \\
      --strategy new_only

  # 采样30%旧数据 + 新数据
  python prepare_incremental_data.py \\
      --new_data datasets/new/train.csv \\
      --old_data datasets/old/train.csv \\
      --output /tmp/prepared_train.csv \\
      --strategy sample \\
      --sample_ratio 0.3

  # 合并全部旧数据 + 新数据
  python prepare_incremental_data.py \\
      --new_data datasets/new/train.csv \\
      --old_data datasets/old/train.csv \\
      --output /tmp/prepared_train.csv \\
      --strategy merge
        """
    )

    parser.add_argument('--new_data', type=str, required=True,
                        help='新训练数据路径')
    parser.add_argument('--old_data', type=str, default='',
                        help='旧训练数据路径（可选）')
    parser.add_argument('--output', type=str, required=True,
                        help='输出数据路径')
    parser.add_argument('--strategy', type=str, default='sample',
                        choices=['sample', 'merge', 'new_only'],
                        help='数据合并策略 (默认: sample)')
    parser.add_argument('--sample_ratio', type=float, default=0.3,
                        help='旧数据采样比例 (默认: 0.3)')
    parser.add_argument('--random_seed', type=int, default=42,
                        help='随机种子 (默认: 42)')
    parser.add_argument('--stats_output', type=str, default='',
                        help='统计信息输出文件路径（可选）')

    args = parser.parse_args()

    # 准备数据
    old_data_path = args.old_data if args.old_data else None
    stats = prepare_incremental_data(
        new_data_path=args.new_data,
        old_data_path=old_data_path,
        output_path=args.output,
        strategy=args.strategy,
        sample_ratio=args.sample_ratio,
        random_seed=args.random_seed
    )

    # 保存统计信息（如果指定）
    if args.stats_output:
        with open(args.stats_output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"📊 统计信息已保存: {args.stats_output}")


if __name__ == '__main__':
    main()
