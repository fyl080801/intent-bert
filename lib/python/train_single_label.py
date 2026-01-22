#!/usr/bin/env python3
"""
单标签分类训练脚本
适用于情感分析等二分类/多分类任务
"""

import os
import json
import argparse
import pandas as pd
import numpy as np
from typing import Dict, List
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
import torch
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
from torch.utils.data import Dataset


class SingleLabelDataset(Dataset):
    """单标签分类数据集"""

    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


def compute_metrics(eval_pred):
    """计算评估指标"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='weighted', zero_division=0
    )

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }


def main():
    parser = argparse.ArgumentParser(description='训练单标签BERT分类模型')
    parser.add_argument('--train_data', type=str, required=True, help='训练数据路径')
    parser.add_argument('--val_data', type=str, required=True, help='验证数据路径')
    parser.add_argument('--model_name', type=str, default='hfl/chinese-roberta-wwm-ext', help='预训练模型名称')
    parser.add_argument('--output_dir', type=str, default='models', help='模型输出目录')
    parser.add_argument('--max_length', type=int, default=128, help='最大序列长度')
    parser.add_argument('--batch_size', type=int, default=32, help='批次大小')
    parser.add_argument('--num_epochs', type=int, default=3, help='训练轮数')
    parser.add_argument('--learning_rate', type=float, default=2e-5, help='学习率')
    parser.add_argument('--warmup_steps', type=int, default=500, help='预热步数')
    parser.add_argument('--weight_decay', type=float, default=0.01, help='权重衰减')
    parser.add_argument('--text_column', type=str, default='sentence', help='文本列名')
    parser.add_argument('--label_column', type=str, default='label', help='标签列名')

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")

    # 加载数据
    print(f"\n加载训练数据: {args.train_data}")
    print(f"加载验证数据: {args.val_data}")

    train_df = pd.read_csv(args.train_data)
    val_df = pd.read_csv(args.val_data)

    print(f"\n数据集统计:")
    print(f"训练集大小: {len(train_df)}")
    print(f"验证集大小: {len(val_df)}")

    # 提取文本和标签
    train_texts = train_df[args.text_column].astype(str).tolist()
    val_texts = val_df[args.text_column].astype(str).tolist()

    # 标签编码
    label_encoder = LabelEncoder()
    all_labels = pd.concat([train_df[args.label_column], val_df[args.label_column]])
    label_encoder.fit(all_labels)

    train_labels = label_encoder.transform(train_df[args.label_column])
    val_labels = label_encoder.transform(val_df[args.label_column])

    num_labels = len(label_encoder.classes_)
    print(f"类别数: {num_labels}")
    print(f"类别名称: {list(label_encoder.classes_)}")

    # 保存标签编码器
    with open(os.path.join(args.output_dir, 'label_encoder.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'classes': label_encoder.classes_.tolist(),
            'num_classes': int(num_labels)
        }, f, ensure_ascii=False, indent=2)

    # 加载 tokenizer
    print(f"\n加载tokenizer: {args.model_name}")
    tokenizer = BertTokenizer.from_pretrained(args.model_name)

    # 创建数据集
    print("\n准备数据集...")
    train_dataset = SingleLabelDataset(
        train_texts,
        train_labels,
        tokenizer,
        args.max_length
    )

    val_dataset = SingleLabelDataset(
        val_texts,
        val_labels,
        tokenizer,
        args.max_length
    )

    print(f"训练批次: {len(train_dataset) // args.batch_size}")
    print(f"验证批次: {len(val_dataset) // args.batch_size}")

    # 加载模型
    print(f"\n初始化BERT模型: {args.model_name}")
    model = BertForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=num_labels
    )
    model.to(device)
    print(f"模型已加载到设备: {device}")

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
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        greater_is_better=True,
        report_to=None,
        save_safetensors=False,  # 使用 PyTorch 原生格式
    )

    # 创建 Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        data_collator=DataCollatorWithPadding(tokenizer),
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
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # 保存最终模型
    print(f"\n保存模型到: {args.output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)

    # 保存训练配置
    config = {
        'model_name': args.model_name,
        'max_length': args.max_length,
        'num_labels': num_labels,
        'label_names': label_encoder.classes_.tolist(),
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

    print("\n训练完成！")
    print(f"模型已保存到: {args.output_dir}")


if __name__ == "__main__":
    main()
