#!/usr/bin/env python3
"""
金融意图BERT多任务学习训练脚本
同时预测一级、二级、三级标签
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
from transformers import DataCollatorForSeq2Seq
from models import BertForMultiLabelClassification, create_multitask_model


class FinancialIntentDataset(Dataset):
    """金融意图分类数据集"""

    def __init__(self, dataframe: pd.DataFrame, tokenizer: BertTokenizer, max_length: int = 128):
        self.dataframe = dataframe
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        text = str(self.dataframe.iloc[idx]['text'])
        labels = {
            'level1': int(self.dataframe.iloc[idx]['label_level1_encoded']),
            'level2': int(self.dataframe.iloc[idx]['label_level2_encoded']),
            'level3': int(self.dataframe.iloc[idx]['label_level3_encoded'])
        }

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
            'labels': labels
        }


class MultiLabelTrainer(Trainer):
    """自定义Trainer，处理多标签分类"""

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        """计算多任务损失"""
        labels = inputs.pop('labels')
        outputs = model(**inputs)

        # 从模型输出中提取logits
        if isinstance(outputs, dict):
            logits1 = outputs['logits_level1']
            logits2 = outputs['logits_level2']
            logits3 = outputs['logits_level3']
        else:
            logits1, logits2, logits3 = outputs

        loss_fct = torch.nn.CrossEntropyLoss()

        loss1 = loss_fct(logits1, labels['level1'])
        loss2 = loss_fct(logits2, labels['level2'])
        loss3 = loss_fct(logits3, labels['level3'])

        # 加权损失（可根据任务重要性调整）
        loss = 0.3 * loss1 + 0.3 * loss2 + 0.4 * loss3

        return (loss, outputs) if return_outputs else loss


def custom_data_collator(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """自定义 data collator，处理多标签数据"""
    batch = {}

    # 处理 input_ids 和 attention_mask
    if 'input_ids' in features[0]:
        batch['input_ids'] = torch.stack([f['input_ids'] for f in features])
    if 'attention_mask' in features[0]:
        batch['attention_mask'] = torch.stack([f['attention_mask'] for f in features])

    # 处理 labels（字典格式）
    if 'labels' in features[0]:
        labels = features[0]['labels']
        batch['labels'] = {
            'level1': torch.tensor([f['labels']['level1'] for f in features]),
            'level2': torch.tensor([f['labels']['level2'] for f in features]),
            'level3': torch.tensor([f['labels']['level3'] for f in features])
        }

    return batch


def compute_metrics(pred) -> Dict[str, float]:
    """计算评估指标"""
    try:
        # 处理模型输出
        predictions = pred.predictions
        label_ids = pred.label_ids

        # 检查是否为 None
        if predictions is None:
            print("Warning: predictions is None")
            return {'overall_accuracy': 0.0}

        if label_ids is None:
            print("Warning: label_ids is None")
            return {'overall_accuracy': 0.0}

        # 处理模型输出 - 支持 dict 和 tuple 格式
        if isinstance(predictions, dict):
            logits1 = predictions['logits_level1']
            logits2 = predictions['logits_level2']
            logits3 = predictions['logits_level3']
        else:
            logits1, logits2, logits3 = predictions

        # 检查 logits 是否为 None
        if logits1 is None or logits2 is None or logits3 is None:
            print(f"Warning: logits are None - l1: {logits1 is not None}, l2: {logits2 is not None}, l3: {logits3 is not None}")
            return {'overall_accuracy': 0.0}

        # 处理标签
        if isinstance(label_ids, dict):
            labels1 = label_ids['level1']
            labels2 = label_ids['level2']
            labels3 = label_ids['level3']
        else:
            labels1, labels2, labels3 = label_ids

        # 检查 labels 是否为 None
        if labels1 is None or labels2 is None or labels3 is None:
            print(f"Warning: labels are None - l1: {labels1 is not None}, l2: {labels2 is not None}, l3: {labels3 is not None}")
            return {'overall_accuracy': 0.0}

        # 确保是 numpy 数组
        if not isinstance(logits1, np.ndarray):
            logits1 = np.array(logits1)
        if not isinstance(logits2, np.ndarray):
            logits2 = np.array(logits2)
        if not isinstance(logits3, np.ndarray):
            logits3 = np.array(logits3)

        if not isinstance(labels1, np.ndarray):
            labels1 = np.array(labels1)
        if not isinstance(labels2, np.ndarray):
            labels2 = np.array(labels2)
        if not isinstance(labels3, np.ndarray):
            labels3 = np.array(labels3)

        preds1 = np.argmax(logits1, axis=1)
        preds2 = np.argmax(logits2, axis=1)
        preds3 = np.argmax(logits3, axis=1)

        metrics = {}

        # 一级标签指标
        precision1, recall1, f1_1, _ = precision_recall_fscore_support(
            labels1, preds1, average='weighted', zero_division=0
        )
        acc1 = accuracy_score(labels1, preds1)
        metrics['level1_accuracy'] = float(acc1)
        metrics['level1_f1'] = float(f1_1)
        metrics['level1_precision'] = float(precision1)
        metrics['level1_recall'] = float(recall1)

        # 二级标签指标
        precision2, recall2, f1_2, _ = precision_recall_fscore_support(
            labels2, preds2, average='weighted', zero_division=0
        )
        acc2 = accuracy_score(labels2, preds2)
        metrics['level2_accuracy'] = float(acc2)
        metrics['level2_f1'] = float(f1_2)
        metrics['level2_precision'] = float(precision2)
        metrics['level2_recall'] = float(recall2)

        # 三级标签指标
        precision3, recall3, f1_3, _ = precision_recall_fscore_support(
            labels3, preds3, average='weighted', zero_division=0
        )
        acc3 = accuracy_score(labels3, preds3)
        metrics['level3_accuracy'] = float(acc3)
        metrics['level3_f1'] = float(f1_3)
        metrics['level3_precision'] = float(precision3)
        metrics['level3_recall'] = float(recall3)

        # 整体准确率（三个层级都正确）
        overall_acc = np.mean((preds1 == labels1) & (preds2 == labels2) & (preds3 == labels3))
        metrics['overall_accuracy'] = float(overall_acc)

        return metrics

    except Exception as e:
        print(f"Error in compute_metrics: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认值而不是抛出异常
        return {
            'level1_accuracy': 0.0,
            'level1_f1': 0.0,
            'level2_accuracy': 0.0,
            'level2_f1': 0.0,
            'level3_accuracy': 0.0,
            'level3_f1': 0.0,
            'overall_accuracy': 0.0
        }


def load_and_prepare_data(train_path: str, val_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """加载和准备数据"""
    print(f"加载训练数据: {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"加载验证数据: {val_path}")
    val_df = pd.read_csv(val_path)

    # 创建标签编码器
    label_encoder_l1 = LabelEncoder()
    label_encoder_l2 = LabelEncoder()
    label_encoder_l3 = LabelEncoder()

    # 训练集编码
    train_df['label_level1_encoded'] = label_encoder_l1.fit_transform(train_df['label_level1'])
    train_df['label_level2_encoded'] = label_encoder_l2.fit_transform(train_df['label_level2'])
    train_df['label_level3_encoded'] = label_encoder_l3.fit_transform(train_df['label_level3'])

    # 验证集编码（使用训练集的编码器）
    val_df['label_level1_encoded'] = label_encoder_l1.transform(val_df['label_level1'])
    val_df['label_level2_encoded'] = label_encoder_l2.transform(val_df['label_level2'])
    val_df['label_level3_encoded'] = label_encoder_l3.transform(val_df['label_level3'])

    # 保存编码器映射
    encoders = {
        'level1': {
            'classes': label_encoder_l1.classes_.tolist(),
            'mapping': {str(k): int(v) for k, v in zip(label_encoder_l1.classes_, label_encoder_l1.transform(label_encoder_l1.classes_))}
        },
        'level2': {
            'classes': label_encoder_l2.classes_.tolist(),
            'mapping': {str(k): int(v) for k, v in zip(label_encoder_l2.classes_, label_encoder_l2.transform(label_encoder_l2.classes_))}
        },
        'level3': {
            'classes': label_encoder_l3.classes_.tolist(),
            'mapping': {str(k): int(v) for k, v in zip(label_encoder_l3.classes_, label_encoder_l3.transform(label_encoder_l3.classes_))}
        }
    }

    print(f"\n数据集统计:")
    print(f"训练集大小: {len(train_df)}")
    print(f"验证集大小: {len(val_df)}")
    print(f"一级标签数: {len(label_encoder_l1.classes_)}")
    print(f"二级标签数: {len(label_encoder_l2.classes_)}")
    print(f"三级标签数: {len(label_encoder_l3.classes_)}")

    return train_df, val_df, encoders


def main():
    parser = argparse.ArgumentParser(description='训练金融意图BERT分类模型')
    parser.add_argument('--train_data', type=str, default='datasets/financial_intent_dataset.csv',
                        help='训练数据路径')
    parser.add_argument('--val_data', type=str, default='datasets/financial_intent_validation.csv',
                        help='验证数据路径')
    parser.add_argument('--model_name', type=str, default='hfl/chinese-roberta-wwm-ext',
                        help='预训练模型名称')
    parser.add_argument('--output_dir', type=str, default='models',
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

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")

    # 加载数据
    train_df, val_df, encoders = load_and_prepare_data(args.train_data, args.val_data)

    # 保存编码器
    with open(os.path.join(args.output_dir, 'label_encoders.json'), 'w', encoding='utf-8') as f:
        json.dump(encoders, f, ensure_ascii=False, indent=2)
    print(f"\n标签编码器已保存到: {os.path.join(args.output_dir, 'label_encoders.json')}")

    # 初始化tokenizer
    print(f"\n加载tokenizer: {args.model_name}")
    tokenizer = BertTokenizer.from_pretrained(args.model_name)

    # 创建数据集
    train_dataset = FinancialIntentDataset(train_df, tokenizer, args.max_length)
    val_dataset = FinancialIntentDataset(val_df, tokenizer, args.max_length)

    # 创建数据加载器
    train_dataloader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_dataloader = DataLoader(val_dataset, batch_size=args.batch_size)

    print(f"\n数据准备完成:")
    print(f"训练批次: {len(train_dataloader)}")
    print(f"验证批次: {len(val_dataloader)}")

    # 创建多任务BERT模型
    print(f"\n初始化多任务BERT模型: {args.model_name}")
    model = create_multitask_model(
        model_name=args.model_name,
        num_level1=len(encoders['level1']['classes']),
        num_level2=len(encoders['level2']['classes']),
        num_level3=len(encoders['level3']['classes'])
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
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="overall_accuracy",
        greater_is_better=True,
        report_to=None,  # 不使用wandb等
        save_safetensors=False,  # 使用 PyTorch 原生格式，避免非连续张量问题
    )

    # 创建Trainer
    trainer = MultiLabelTrainer(
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
        'max_length': args.max_length,
        'num_labels': {
            'level1': len(encoders['level1']['classes']),
            'level2': len(encoders['level2']['classes']),
            'level3': len(encoders['level3']['classes'])
        },
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
