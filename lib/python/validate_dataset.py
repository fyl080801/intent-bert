#!/usr/bin/env python3
"""
数据集验证脚本
验证数据集格式是否符合规范，支持单标签、多标签和多级标签数据集
"""

import pandas as pd
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any


class DatasetValidator:
    """数据集验证器"""

    def __init__(self, registry_path: str = "datasets/dataset_registry.json"):
        """
        初始化验证器

        Args:
            registry_path: 数据集注册表路径
        """
        self.registry_path = registry_path
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        """加载数据集注册表"""
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate_dataset(self, dataset_name: str) -> Tuple[bool, List[str], List[str]]:
        """
        验证指定数据集

        Args:
            dataset_name: 数据集名称（在注册表中定义的key）

        Returns:
            (is_valid, errors, warnings) 验证结果
        """
        if dataset_name not in self.registry['datasets']:
            return False, [f"数据集 '{dataset_name}' 未在注册表中定义"], []

        dataset_config = self.registry['datasets'][dataset_name]
        errors = []
        warnings = []

        # 验证数据文件存在性
        data_paths = dataset_config.get('data_paths', {})
        for split_name, file_path in data_paths.items():
            if not Path(file_path).exists():
                errors.append(f"{split_name} 数据文件不存在: {file_path}")

        if errors:
            return False, errors, warnings

        # 验证数据格式
        for split_name, file_path in data_paths.items():
            split_errors, split_warnings = self._validate_data_file(
                file_path, dataset_config
            )
            errors.extend([f"{split_name}: {e}" for e in split_errors])
            warnings.extend([f"{split_name}: {w}" for w in split_warnings])

        # 验证配置文件（如果存在）
        config_path = dataset_config.get('config_path')
        if config_path:
            config_errors = self._validate_config_file(config_path, dataset_config)
            errors.extend(config_errors)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def _validate_data_file(
        self, file_path: str, config: Dict
    ) -> Tuple[List[str], List[str]]:
        """
        验证单个数据文件

        Args:
            file_path: 数据文件路径
            config: 数据集配置

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            errors.append(f"无法读取CSV文件: {str(e)}")
            return errors, warnings

        # 基本检查
        if len(df) == 0:
            errors.append("数据集为空")
            return errors, warnings

        # 检查必需列
        task_type = config.get('task_type')
        text_column = config.get('text_column', 'text')
        label_columns = config.get('label_columns', [])

        # 检查文本列
        if text_column not in df.columns:
            errors.append(f"缺少文本列 '{text_column}'")
        else:
            # 检查空值
            null_count = df[text_column].isnull().sum()
            if null_count > 0:
                warnings.append(f"文本列 '{text_column}' 有 {null_count} 个空值")

            # 检查文本长度
            if text_column in df.columns:
                avg_length = df[text_column].str.len().mean()
                max_length = df[text_column].str.len().max()
                warnings.append(f"文本长度统计 - 平均: {avg_length:.1f}, 最大: {max_length}")

        # 根据任务类型验证标签列
        if task_type == "single_label":
            errors.extend(self._validate_single_label(df, label_columns, config))
        elif task_type == "multi_label":
            errors.extend(self._validate_multi_label(df, label_columns, config))
        elif task_type == "hierarchical":
            errors.extend(self._validate_hierarchical(df, label_columns, config))

        return errors, warnings

    def _validate_single_label(
        self, df: pd.DataFrame, label_columns: List[str], config: Dict
    ) -> List[str]:
        """验证单标签数据集"""
        errors = []

        if not label_columns:
            errors.append("单标签数据集必须指定 label_columns")
            return errors

        label_col = label_columns[0]
        if label_col not in df.columns:
            errors.append(f"缺少标签列 '{label_col}'")
            return errors

        # 检查标签值
        unique_labels = df[label_col].unique()
        num_labels = config.get('num_labels')

        if num_labels and len(unique_labels) > num_labels:
            errors.append(
                f"标签数量 ({len(unique_labels)}) 超过配置的 num_labels ({num_labels})"
            )

        # 检查空值
        null_count = df[label_col].isnull().sum()
        if null_count > 0:
            errors.append(f"标签列 '{label_col}' 有 {null_count} 个空值")

        return errors

    def _validate_multi_label(
        self, df: pd.DataFrame, label_columns: List[str], config: Dict
    ) -> List[str]:
        """验证多标签数据集"""
        errors = []

        if not label_columns:
            errors.append("多标签数据集必须指定 label_columns")
            return errors

        label_col = label_columns[0]
        if label_col not in df.columns:
            errors.append(f"缺少标签列 '{label_col}'")
            return errors

        # 检查标签格式（应该是列表或JSON字符串）
        try:
            sample_labels = df[label_col].iloc[0]
            if isinstance(sample_labels, str):
                # 尝试解析为JSON
                json.loads(sample_labels)
        except Exception as e:
            errors.append(f"多标签列 '{label_col}' 格式错误: {str(e)}")

        return errors

    def _validate_hierarchical(
        self, df: pd.DataFrame, label_columns: List[str], config: Dict
    ) -> List[str]:
        """验证层级标签数据集"""
        errors = []

        if not label_columns:
            errors.append("层级标签数据集必须指定 label_columns")
            return errors

        # 检查所有层级列
        for label_col in label_columns:
            if label_col not in df.columns:
                errors.append(f"缺少层级标签列 '{label_col}'")

        # 检查层级完整性
        if all(col in df.columns for col in label_columns):
            # 检查是否存在父级为空但子级不为空的情况
            for i in range(1, len(label_columns)):
                parent_col = label_columns[i-1]
                child_col = label_columns[i]

                # 父级为空时，子级也应该为空
                parent_null = df[parent_col].isnull()
                child_not_null = df[child_col].notnull()
                invalid_rows = (parent_null & child_not_null).sum()

                if invalid_rows > 0:
                    errors.append(
                        f"存在 {invalid_rows} 行数据: 父级 '{parent_col}' 为空但子级 '{child_col}' 不为空"
                    )

        return errors

    def _validate_config_file(self, config_path: str, dataset_config: Dict) -> List[str]:
        """验证配置文件"""
        errors = []

        if not Path(config_path).exists():
            errors.append(f"配置文件不存在: {config_path}")
            return errors

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            errors.append(f"配置文件JSON格式错误: {str(e)}")
            return errors

        # 根据任务类型验证配置内容
        task_type = dataset_config.get('task_type')
        if task_type == "hierarchical":
            if 'labels' not in config:
                errors.append("层级配置文件必须包含 'labels' 字段")

        return errors

    def print_validation_report(self, dataset_name: str):
        """打印验证报告"""
        is_valid, errors, warnings = self.validate_dataset(dataset_name)

        print("\n" + "=" * 60)
        print(f"数据集验证报告: {dataset_name}")
        print("=" * 60)

        # 显示数据集信息
        if dataset_name in self.registry['datasets']:
            config = self.registry['datasets'][dataset_name]
            print(f"\n数据集名称: {config.get('name')}")
            print(f"任务类型: {config.get('task_type')}")
            print(f"标签类型: {config.get('label_type')}")
            print(f"描述: {config.get('description')}")

        # 显示验证结果
        print("\n" + "-" * 60)
        if is_valid:
            print("✓ 验证通过")
        else:
            print("✗ 验证失败")

        # 显示错误
        if errors:
            print(f"\n错误 ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")

        # 显示警告
        if warnings:
            print(f"\n警告 ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")

        print("=" * 60 + "\n")

        return is_valid

    def validate_all_datasets(self) -> Dict[str, bool]:
        """验证所有注册的数据集"""
        results = {}

        for dataset_name in self.registry['datasets'].keys():
            print(f"\n正在验证数据集: {dataset_name}...")
            is_valid = self.print_validation_report(dataset_name)
            results[dataset_name] = is_valid

        # 汇总报告
        print("\n" + "=" * 60)
        print("验证汇总")
        print("=" * 60)
        valid_count = sum(results.values())
        total_count = len(results)

        for dataset_name, is_valid in results.items():
            status = "✓ 通过" if is_valid else "✗ 失败"
            print(f"  {dataset_name}: {status}")

        print(f"\n总计: {valid_count}/{total_count} 个数据集验证通过")
        print("=" * 60 + "\n")

        return results


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='验证数据集格式')
    parser.add_argument(
        '--dataset',
        type=str,
        default=None,
        help='指定数据集名称（不指定则验证所有数据集）'
    )
    parser.add_argument(
        '--registry',
        type=str,
        default='datasets/dataset_registry.json',
        help='数据集注册表路径'
    )

    args = parser.parse_args()

    validator = DatasetValidator(args.registry)

    if args.dataset:
        # 验证单个数据集
        is_valid = validator.print_validation_report(args.dataset)
        sys.exit(0 if is_valid else 1)
    else:
        # 验证所有数据集
        results = validator.validate_all_datasets()
        all_valid = all(results.values())
        sys.exit(0 if all_valid else 1)


if __name__ == '__main__':
    main()
