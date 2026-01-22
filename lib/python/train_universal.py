#!/usr/bin/env python3
"""
通用BERT训练脚本
支持单标签、多标签和多级标签的统一训练接口
"""

import os
import sys
import json
import argparse
import pandas as pd
import torch
from pathlib import Path
from typing import Dict, Any, Optional

# 添加lib/python到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# 导入不同的训练器和模型
from train import main as train_fixed_main
from train_dynamic import main as train_dynamic_main


class DatasetConfigLoader:
    """从数据集注册表加载配置"""

    def __init__(self, registry_path: str = "datasets/dataset_registry.json"):
        self.registry_path = registry_path
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        """加载注册表"""
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_dataset_config(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """获取指定数据集的配置"""
        return self.registry['datasets'].get(dataset_name)

    def list_datasets(self) -> Dict[str, str]:
        """列出所有注册的数据集"""
        return {
            name: config.get('name', name)
            for name, config in self.registry['datasets'].items()
        }


class UniversalTrainer:
    """通用训练器 - 根据数据集类型选择合适的训练方法"""

    def __init__(self, registry_path: str = "datasets/dataset_registry.json"):
        self.config_loader = DatasetConfigLoader(registry_path)

    def train(self, dataset_name: str, **kwargs) -> bool:
        """
        根据数据集类型执行训练

        Args:
            dataset_name: 数据集名称
            **kwargs: 额外的训练参数

        Returns:
            训练是否成功
        """
        # 加载数据集配置
        dataset_config = self.config_loader.get_dataset_config(dataset_name)
        if not dataset_config:
            print(f"错误: 未找到数据集 '{dataset_name}' 的配置")
            return False

        print(f"\n{'='*60}")
        print(f"开始训练数据集: {dataset_name}")
        print(f"{'='*60}")
        print(f"数据集名称: {dataset_config.get('name')}")
        print(f"任务类型: {dataset_config.get('task_type')}")
        print(f"标签类型: {dataset_config.get('label_type')}")
        print(f"训练脚本: {dataset_config.get('training_script')}")
        print(f"{'='*60}\n")

        # 根据训练脚本选择训练方法
        training_script = dataset_config.get('training_script')

        try:
            if training_script == "train.py":
                # 固定层级训练
                return self._train_fixed(dataset_config, **kwargs)
            elif training_script == "train_dynamic.py":
                # 动态层级训练
                return self._train_dynamic(dataset_config, **kwargs)
            elif training_script == "train_single_label.py":
                # 单标签训练
                return self._train_single_label(dataset_config, **kwargs)
            else:
                print(f"错误: 不支持的训练脚本类型 '{training_script}'")
                return False
        except Exception as e:
            print(f"训练失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _train_fixed(self, dataset_config: Dict, **kwargs) -> bool:
        """执行固定层级训练"""
        data_paths = dataset_config['data_paths']

        # 构建参数
        args = [
            '--train_data', data_paths['train'],
            '--val_data', data_paths['validation'],
            '--model_name', kwargs.get('model_name', 'bert-base-chinese'),
            '--output_dir', kwargs.get('output_dir', 'models_fixed'),
            '--batch_size', str(kwargs.get('batch_size', 16)),
            '--num_epochs', str(kwargs.get('num_epochs', 5)),
            '--learning_rate', str(kwargs.get('learning_rate', 2e-5)),
            '--max_length', str(kwargs.get('max_length', 128)),
            '--warmup_steps', str(kwargs.get('warmup_steps', 500)),
            '--weight_decay', str(kwargs.get('weight_decay', 0.01)),
        ]

        # 模拟命令行参数
        import sys
        old_argv = sys.argv
        sys.argv = ['train.py'] + args

        try:
            train_fixed_main()
            return True
        except SystemExit as e:
            return e.code == 0
        finally:
            sys.argv = old_argv

    def _train_dynamic(self, dataset_config: Dict, **kwargs) -> bool:
        """执行动态层级训练"""
        data_paths = dataset_config['data_paths']
        config_path = dataset_config.get('config_path')

        if not config_path or not Path(config_path).exists():
            print(f"错误: 配置文件不存在: {config_path}")
            return False

        # 构建参数
        args = [
            '--train_data', data_paths['train'],
            '--val_data', data_paths['validation'],
            '--hierarchy_config', config_path,
            '--model_name', kwargs.get('model_name', 'bert-base-chinese'),
            '--output_dir', kwargs.get('output_dir', 'models_dynamic'),
            '--batch_size', str(kwargs.get('batch_size', 16)),
            '--num_epochs', str(kwargs.get('num_epochs', 5)),
            '--learning_rate', str(kwargs.get('learning_rate', 2e-5)),
            '--max_length', str(kwargs.get('max_length', 128)),
            '--warmup_steps', str(kwargs.get('warmup_steps', 500)),
            '--weight_decay', str(kwargs.get('weight_decay', 0.01)),
            '--model_version', kwargs.get('model_version', 'v1'),
        ]

        import sys
        old_argv = sys.argv
        sys.argv = ['train_dynamic.py'] + args

        try:
            train_dynamic_main()
            return True
        except SystemExit as e:
            return e.code == 0
        finally:
            sys.argv = old_argv

    def _train_single_label(self, dataset_config: Dict, **kwargs) -> bool:
        """执行单标签训练（需要实现 train_single_label.py）"""
        print("注意: 单标签训练功能需要实现 train_single_label.py")
        print("作为临时方案，使用标准的transformers训练...")

        # TODO: 实现专用的单标签训练脚本
        # 这里可以使用HuggingFace的Trainer API快速实现
        data_paths = dataset_config['data_paths']

        print(f"\n训练数据: {data_paths['train']}")
        print(f"验证数据: {data_paths['validation']}")
        print(f"标签数: {dataset_config.get('num_labels', 2)}")

        # 临时使用简单的transformers训练
        return self._train_with_transformers(dataset_config, **kwargs)

    def _train_with_transformers(self, dataset_config: Dict, **kwargs) -> bool:
        """使用transformers库进行快速训练"""
        try:
            from transformers import (
                AutoTokenizer, AutoModelForSequenceClassification,
                TrainingArguments, Trainer, DataCollatorWithPadding
            )
            from datasets import Dataset as HFDataset
            import numpy as np
            from sklearn.metrics import accuracy_score, f1_score

            data_paths = dataset_config['data_paths']
            text_column = dataset_config.get('text_column', 'text')
            label_column = dataset_config['label_columns'][0]
            num_labels = dataset_config.get('num_labels', 2)
            model_name = kwargs.get('model_name', 'bert-base-chinese')

            # 加载数据
            train_df = pd.read_csv(data_paths['train'])
            val_df = pd.read_csv(data_paths['validation'])

            print(f"训练集大小: {len(train_df)}")
            print(f"验证集大小: {len(val_df)}")

            # 转换为HuggingFace Dataset
            train_dataset = HFDataset.from_pandas(train_df)
            val_dataset = HFDataset.from_pandas(val_df)

            # 加载tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)

            def preprocess_function(examples):
                # 确保输入是字符串列表
                texts = examples[text_column]
                if not isinstance(texts, list):
                    texts = [texts]
                # 确保所有元素都是字符串
                texts = [str(t) if not isinstance(t, str) else t for t in texts]

                return tokenizer(
                    texts,
                    truncation=True,
                    max_length=kwargs.get('max_length', 128),
                    padding=False
                )

            # 处理数据
            train_dataset = train_dataset.map(
                preprocess_function,
                batched=True,
                remove_columns=train_dataset.column_names
            )
            val_dataset = val_dataset.map(
                preprocess_function,
                batched=True,
                remove_columns=val_dataset.column_names
            )

            # 添加标签
            train_dataset = train_dataset.add_column(
                'labels',
                train_df[label_column].tolist()
            )
            val_dataset = val_dataset.add_column(
                'labels',
                val_df[label_column].tolist()
            )

            # 加载模型
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=num_labels
            )

            # 训练参数
            training_args = TrainingArguments(
                output_dir=kwargs.get('output_dir', 'models_single_label'),
                learning_rate=kwargs.get('learning_rate', 2e-5),
                per_device_train_batch_size=kwargs.get('batch_size', 16),
                per_device_eval_batch_size=kwargs.get('batch_size', 16),
                num_train_epochs=kwargs.get('num_epochs', 5),
                weight_decay=kwargs.get('weight_decay', 0.01),
                eval_strategy="epoch",
                save_strategy="epoch",
                load_best_model_at_end=True,
                logging_dir=f"{kwargs.get('output_dir', 'models_single_label')}/logs",
                report_to=None,
            )

            # 评估函数
            def compute_metrics(eval_pred):
                predictions, labels = eval_pred
                predictions = np.argmax(predictions, axis=1)
                return {
                    'accuracy': accuracy_score(labels, predictions),
                    'f1': f1_score(labels, predictions, average='weighted')
                }

            # Trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
                tokenizer=tokenizer,
                data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
                compute_metrics=compute_metrics,
            )

            # 训练
            print("\n开始训练...")
            trainer.train()

            # 评估
            print("\n评估模型...")
            eval_results = trainer.evaluate()

            # 保存模型
            output_dir = kwargs.get('output_dir', 'models_single_label')
            trainer.save_model(output_dir)
            tokenizer.save_pretrained(output_dir)

            # 保存配置
            config = {
                'dataset_name': kwargs.get('dataset_name', 'unknown'),
                'model_name': model_name,
                'num_labels': num_labels,
                'task_type': 'single_label',
                'eval_results': eval_results
            }
            with open(f"{output_dir}/training_config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            print(f"\n训练完成！模型已保存到: {output_dir}")
            print(f"评估准确率: {eval_results.get('eval_accuracy', 0):.4f}")

            return True

        except Exception as e:
            print(f"训练失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通用BERT训练脚本')

    # 必需参数
    parser.add_argument('--dataset', type=str, required=True,
                       help='数据集名称（在dataset_registry.json中定义）')

    # 可选参数（会覆盖数据集配置）
    parser.add_argument('--model_name', type=str, default=None,
                       help='预训练模型名称')
    parser.add_argument('--output_dir', type=str, default=None,
                       help='模型输出目录')
    parser.add_argument('--batch_size', type=int, default=None,
                       help='批次大小')
    parser.add_argument('--num_epochs', type=int, default=None,
                       help='训练轮数')
    parser.add_argument('--learning_rate', type=float, default=None,
                       help='学习率')
    parser.add_argument('--max_length', type=int, default=None,
                       help='最大序列长度')
    parser.add_argument('--warmup_steps', type=int, default=None,
                       help='预热步数')
    parser.add_argument('--weight_decay', type=float, default=None,
                       help='权重衰减')
    parser.add_argument('--model_version', type=str, default='v1',
                       choices=['v1', 'v2'],
                       help='动态模型版本')
    parser.add_argument('--registry', type=str,
                       default='datasets/dataset_registry.json',
                       help='数据集注册表路径')

    # 工具参数
    parser.add_argument('--list_datasets', action='store_true',
                       help='列出所有可用的数据集')

    args = parser.parse_args()

    # 初始化训练器
    trainer = UniversalTrainer(args.registry)

    # 列出数据集
    if args.list_datasets:
        print("\n可用的数据集:")
        print("=" * 60)
        for name, display_name in trainer.config_loader.list_datasets().items():
            print(f"  - {name}: {display_name}")
        print("=" * 60 + "\n")
        return

    # 过滤掉None值，使用数据集配置的默认值
    train_kwargs = {}
    for key, value in vars(args).items():
        if key not in ['dataset', 'registry', 'list_datasets'] and value is not None:
            train_kwargs[key] = value

    train_kwargs['dataset_name'] = args.dataset

    # 执行训练
    success = trainer.train(**train_kwargs)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
