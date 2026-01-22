#!/usr/bin/env python3
"""
动态层级BERT多任务学习训练脚本
支持灵活的多级标签结构训练
"""

import os
import json
import argparse
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, TrainingArguments, Trainer
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
from typing import Dict, List, Tuple, Any
import numpy as np

# 导入动态模型和配置解析器
from dynamic_models import BertForDynamicHierarchicalClassification, create_dynamic_model
from hierarchy_config import HierarchyConfigParser, create_label_encoders


class DynamicHierarchicalDataset(Dataset):
    """支持可变层级深度的数据集"""

    def __init__(self, dataframe: pd.DataFrame, tokenizer: BertTokenizer,
                 hierarchy_info: Dict, max_length: int = 128):
        """
        初始化数据集

        Args:
            dataframe: 包含标签的数据框
            tokenizer: BERT分词器
            hierarchy_info: 层级配置信息
            max_length: 最大序列长度
        """
        self.dataframe = dataframe
        self.tokenizer = tokenizer
        self.hierarchy_info = hierarchy_info
        self.max_length = max_length
        self.num_levels = hierarchy_info['num_levels']
        self.level_labels = hierarchy_info['level_labels']

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        text = str(self.dataframe.iloc[idx]['text'])

        # 获取该样本的所有层级标签
        labels = []
        actual_depth = 0

        for level_idx in range(self.num_levels):
            label_col = f'label_level{level_idx + 1}'
            if label_col in self.dataframe.columns:
                label_value = self.dataframe.iloc[idx][label_col]

                # 检查是否为有效标签
                if pd.notna(label_value) and label_value != '':
                    # 将字符串标签转换为编码
                    label_str = str(label_value)
                    if label_str in self.level_labels[level_idx]:
                        # 找到标签在当前层的索引
                        label_idx = self.level_labels[level_idx].index(label_str)
                        labels.append(label_idx)
                        actual_depth += 1
                    else:
                        # 标签不在当前层级，停止
                        break
                else:
                    break
            else:
                break

        # 如果没有标签，使用-1填充
        while len(labels) < self.num_levels:
            labels.append(-1)

        # 编码文本
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(labels, dtype=torch.long),
            'actual_depth': actual_depth
        }


class DynamicMultiLabelTrainer(Trainer):
    """自定义Trainer，处理动态多层级分类"""

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        """计算支持可变深度的多层级损失"""
        labels = inputs.pop('labels')
        actual_depths = inputs.pop('actual_depth')

        outputs = model(**inputs)
        all_logits = outputs['logits']

        loss_fct = torch.nn.CrossEntropyLoss(ignore_index=-1)
        total_loss = 0
        valid_counts = 0

        # 对每个层级计算loss
        for level_idx, logits in enumerate(all_logits):
            level_labels = labels[:, level_idx]

            # 只计算非-1的标签
            valid_mask = level_labels >= 0
            if valid_mask.sum() > 0:
                valid_logits = logits[valid_mask]
                valid_labels = level_labels[valid_mask]

                level_loss = loss_fct(valid_logits, valid_labels)
                total_loss += level_loss
                valid_counts += 1

        # 平均所有有效层级的loss
        avg_loss = total_loss / valid_counts if valid_counts > 0 else 0

        return (avg_loss, outputs) if return_outputs else avg_loss


def custom_data_collator(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """自定义data collator，处理动态多层级数据"""
    batch = {}

    # 处理 input_ids 和 attention_mask
    if 'input_ids' in features[0]:
        batch['input_ids'] = torch.stack([f['input_ids'] for f in features])
    if 'attention_mask' in features[0]:
        batch['attention_mask'] = torch.stack([f['attention_mask'] for f in features])

    # 处理 labels
    if 'labels' in features[0]:
        labels_tensor = torch.stack([f['labels'] for f in features])
        batch['labels'] = labels_tensor

    # 处理 actual_depth
    if 'actual_depth' in features[0]:
        batch['actual_depth'] = torch.tensor([f['actual_depth'] for f in features])

    return batch


def compute_metrics(pred) -> Dict[str, float]:
    """计算评估指标"""
    try:
        predictions = pred.predictions
        label_ids = pred.label_ids

        if predictions is None or label_ids is None:
            return {'overall_accuracy': 0.0}

        # 处理模型输出
        if isinstance(predictions, dict) and 'logits' in predictions:
            all_logits = predictions['logits']
        elif isinstance(predictions, dict):
            # 可能是嵌套的logits
            all_logits = predictions.get('logits', [])
        else:
            # 假设是列表或元组
            all_logits = predictions

        metrics = {}
        all_correct = None

        # 对每个层级计算指标
        for level_idx, logits in enumerate(all_logits):
            if not isinstance(logits, np.ndarray):
                logits = np.array(logits)

            preds_level = np.argmax(logits, axis=1)

            # 获取对应层级的标签
            if isinstance(label_ids, dict):
                labels_level = label_ids.get(f'level{level_idx}', label_ids.get('level1'))
            else:
                labels_level = label_ids[:, level_idx] if len(label_ids.shape) > 1 else label_ids

            if not isinstance(labels_level, np.ndarray):
                labels_level = np.array(labels_level)

            # 只计算有效标签（非-1）
            valid_mask = labels_level >= 0
            if valid_mask.sum() > 0:
                valid_preds = preds_level[valid_mask]
                valid_labels = labels_level[valid_mask]

                precision, recall, f1, _ = precision_recall_fscore_support(
                    valid_labels, valid_preds, average='weighted', zero_division=0
                )
                acc = accuracy_score(valid_labels, valid_preds)

                metrics[f'level{level_idx}_accuracy'] = float(acc)
                metrics[f'level{level_idx}_f1'] = float(f1)
                metrics[f'level{level_idx}_precision'] = float(precision)
                metrics[f'level{level_idx}_recall'] = float(recall)

                # 累积整体准确率
                if all_correct is None:
                    all_correct = (valid_preds == valid_labels)
                else:
                    all_correct = all_correct & (valid_preds == valid_labels)

        # 计算整体准确率
        if all_correct is not None:
            metrics['overall_accuracy'] = float(np.mean(all_correct))
        else:
            metrics['overall_accuracy'] = 0.0

        return metrics

    except Exception as e:
        print(f"Error in compute_metrics: {e}")
        import traceback
        traceback.print_exc()
        return {'overall_accuracy': 0.0}


def load_and_prepare_data(train_path: str, val_path: str, hierarchy_info: Dict) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """加载和准备数据，使用层级配置信息"""
    print(f"加载训练数据: {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"加载验证数据: {val_path}")
    val_df = pd.read_csv(val_path)

    # 使用层级配置中的标签顺序
    level_labels = hierarchy_info['level_labels']

    # 创建编码器映射（保持与配置文件一致的顺序）
    encoders = {}
    for level_idx, labels in level_labels.items():
        encoders[f'level{level_idx}'] = {
            'classes': labels,
            'mapping': {label: idx for idx, label in enumerate(labels)}
        }

    print(f"\n数据集统计:")
    print(f"训练集大小: {len(train_df)}")
    print(f"验证集大小: {len(val_df)}")
    for level_idx in range(hierarchy_info['num_levels']):
        labels = level_labels[level_idx]
        print(f"Level {level_idx} 标签数: {len(labels)}")

    return train_df, val_df, encoders


def main():
    parser = argparse.ArgumentParser(description='训练动态层级BERT分类模型')
    parser.add_argument('--train_data', type=str, default='datasets/financial_intent_dataset.csv',
                        help='训练数据路径')
    parser.add_argument('--val_data', type=str, default='datasets/financial_intent_validation.csv',
                        help='验证数据路径')
    parser.add_argument('--hierarchy_config', type=str, default='datasets/hierarchy_config.json',
                        help='层级配置文件路径')
    parser.add_argument('--model_name', type=str, default='hfl/chinese-roberta-wwm-ext',
                        help='预训练模型名称')
    parser.add_argument('--output_dir', type=str, default='models_dynamic',
                        help='模型输出目录')
    parser.add_argument('--max_length', type=int, default=128,
                        help='最大序列长度')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='批次大小')
    parser.add_argument('--num_epochs', type=int, default=5,
                        help='训练轮数')
    parser.add_argument('--learning_rate', type=float, default=2e-5,
                        help='学习率')
    parser.add_argument('--warmup_steps', type=int, default=500,
                        help='预热步数')
    parser.add_argument('--weight_decay', type=float, default=0.01,
                        help='权重衰减')
    parser.add_argument('--model_version', type=str, default='v1',
                        choices=['v1', 'v2'],
                        help='模型版本')

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")

    # 解析层级配置
    print(f"\n解析层级配置: {args.hierarchy_config}")
    hierarchy_parser = HierarchyConfigParser(args.hierarchy_config)
    hierarchy_parser.print_summary()

    hierarchy_info = hierarchy_parser.get_hierarchy_info()

    # 保存标签映射
    label_mapping_path = os.path.join(args.output_dir, 'hierarchical_label_mapping.json')
    hierarchy_parser.save_label_mapping(label_mapping_path)

    # 加载数据
    train_df, val_df, encoders = load_and_prepare_data(
        args.train_data, args.val_data, hierarchy_info
    )

    # 保存编码器
    with open(os.path.join(args.output_dir, 'label_encoders.json'), 'w', encoding='utf-8') as f:
        json.dump(encoders, f, ensure_ascii=False, indent=2)
    print(f"\n标签编码器已保存到: {os.path.join(args.output_dir, 'label_encoders.json')}")

    # 初始化tokenizer
    print(f"\n加载tokenizer: {args.model_name}")
    tokenizer = BertTokenizer.from_pretrained(args.model_name)

    # 创建数据集
    train_dataset = DynamicHierarchicalDataset(train_df, tokenizer, hierarchy_info, args.max_length)
    val_dataset = DynamicHierarchicalDataset(val_df, tokenizer, hierarchy_info, args.max_length)

    print(f"\n数据准备完成:")
    print(f"训练集大小: {len(train_dataset)}")
    print(f"验证集大小: {len(val_dataset)}")

    # 创建动态层级BERT模型
    print(f"\n初始化动态层级BERT模型 (v{args.model_version}): {args.model_name}")
    model_config = hierarchy_parser.get_model_config()

    model = create_dynamic_model(
        model_name=args.model_name,
        hierarchy_config=model_config,
        model_version=args.model_version
    )
    model.to(device)
    print(f"模型已加载到设备: {device}")

    # 打印模型信息
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"总参数量: {total_params:,}")
    print(f"可训练参数: {trainable_params:,}")

    # 训练参数
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        warmup_steps=args.warmup_steps,
        weight_decay=args.weight_decay,
        learning_rate=args.learning_rate,
        logging_dir=f'{args.output_dir}/logs',
        logging_steps=100,
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="overall_accuracy",
        greater_is_better=True,
        report_to=None,
    )

    # 创建Trainer
    trainer = DynamicMultiLabelTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        data_collator=custom_data_collator,
    )

    # 开始训练
    print("\n开始训练...")
    print("=" * 50)
    trainer.train()

    # 评估模型
    print("\n训练完成，评估模型...")
    print("=" * 50)
    eval_results = trainer.evaluate()

    # 保存评估结果
    with open(os.path.join(args.output_dir, 'eval_results.json'), 'w', encoding='utf-8') as f:
        json.dump(eval_results, f, ensure_ascii=False, indent=2)

    print("\n评估结果:")
    for key, value in eval_results.items():
        print(f"  {key}: {value:.4f}")

    # 保存最终模型
    print(f"\n保存模型到: {args.output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)

    # 保存训练配置
    config = {
        'model_name': args.model_name,
        'model_version': args.model_version,
        'hierarchy_config': model_config,
        'max_length': args.max_length,
        'training_args': {
            'batch_size': args.batch_size,
            'num_epochs': args.num_epochs,
            'learning_rate': args.learning_rate,
            'warmup_steps': args.warmup_steps,
            'weight_decay': args.weight_decay
        },
        'eval_results': eval_results
    }

    with open(os.path.join(args.output_dir, 'training_config.json'), 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n训练配置已保存到: {os.path.join(args.output_dir, 'training_config.json')}")
    print("\n训练完成！")
    print(f"模型已保存到: {args.output_dir}")


if __name__ == '__main__':
    main()
