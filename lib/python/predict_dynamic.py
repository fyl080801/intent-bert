#!/usr/bin/env python3
"""
动态层级BERT预测脚本
支持灵活的多级标签结构预测
"""

import os
import json
import argparse
import torch
from typing import Dict, List, Union, Optional
from pathlib import Path
import pandas as pd

from transformers import BertTokenizer
from dynamic_models import BertForDynamicHierarchicalClassification, create_dynamic_model
from hierarchy_config import HierarchyConfigParser


class DynamicHierarchicalPredictor:
    """动态层级预测器"""

    def __init__(self, model_path: str, hierarchy_config_path: str = None,
                 label_mapping_path: str = None, device: str = 'auto'):
        """
        初始化预测器

        Args:
            model_path: 训练好的模型路径
            hierarchy_config_path: 层级配置文件路径（可选）
            label_mapping_path: 标签映射文件路径（可选）
            device: 设备 ('auto', 'cuda', 'cpu')
        """
        self.model_path = model_path

        # 设置设备
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"使用设备: {self.device}")

        # 加载标签映射
        if label_mapping_path and os.path.exists(label_mapping_path):
            with open(label_mapping_path, 'r', encoding='utf-8') as f:
                label_mapping = json.load(f)
            self.level_labels = label_mapping['level_labels']
            self.hierarchy_config = label_mapping['config']
            print(f"从标签映射加载配置")
        elif hierarchy_config_path:
            parser = HierarchyConfigParser(hierarchy_config_path)
            hierarchy_info = parser.get_hierarchy_info()
            self.level_labels = hierarchy_info['level_labels']
            self.hierarchy_config = parser.get_model_config()
            print(f"从层级配置文件加载")
        else:
            # 尝试从模型目录加载
            config_path = os.path.join(model_path, 'hierarchical_label_mapping.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    label_mapping = json.load(f)
                self.level_labels = label_mapping['level_labels']
                self.hierarchy_config = label_mapping['config']
                print(f"从模型目录加载标签映射")
            else:
                raise ValueError(f"找不到配置文件: {config_path}")

        # 加载tokenizer
        print(f"加载tokenizer...")
        self.tokenizer = BertTokenizer.from_pretrained(model_path)

        # 加载模型
        print(f"加载模型: {model_path}")
        self.model = create_dynamic_model(
            model_name=model_path,
            hierarchy_config=self.hierarchy_config,
            model_version='v1'
        )
        self.model.to(self.device)
        self.model.eval()

        print(f"✅ 预测器初始化完成")
        print(f"层级数: {self.hierarchy_config['num_levels']}")
        for i, size in enumerate(self.hierarchy_config['level_sizes']):
            print(f"  Level {i}: {size} 个标签")

    def predict_single(self, text: str, max_length: int = 128,
                       return_all_levels: bool = True) -> Dict:
        """
        预测单条文本

        Args:
            text: 输入文本
            max_length: 最大序列长度
            return_all_levels: 是否返回所有层级

        Returns:
            预测结果字典
        """
        # 编码文本
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=max_length,
            return_tensors='pt'
        )

        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        # 预测
        with torch.no_grad():
            outputs = self.model.predict(input_ids, attention_mask, return_all_levels=True)

        # 解析结果
        predictions = []
        confidences = []
        full_path = []

        for level_idx in range(len(outputs['predictions'])):
            pred_idx = outputs['predictions'][level_idx][0].item()
            conf = outputs['confidences'][level_idx][0].item()

            if pred_idx < len(self.level_labels[level_idx]):
                label = self.level_labels[level_idx][pred_idx]
                predictions.append({
                    'level': level_idx,
                    'name': label,
                    'label': label,
                    'confidence': float(conf)
                })
                confidences.append(float(conf))
                full_path.append(label)

        result = {
            'text': text,
            'predictions': predictions if return_all_levels else predictions[-1:],
            'full_path': ' > '.join(full_path),
            'confidence_avg': sum(confidences) / len(confidences) if confidences else 0.0,
            'num_levels': len(predictions)
        }

        return result

    def predict_batch(self, texts: List[str], max_length: int = 128,
                      return_all_levels: bool = True) -> List[Dict]:
        """
        批量预测

        Args:
            texts: 文本列表
            max_length: 最大序列长度
            return_all_levels: 是否返回所有层级

        Returns:
            预测结果列表
        """
        results = []

        # 批量编码
        encodings = self.tokenizer(
            texts,
            truncation=True,
            padding='max_length',
            max_length=max_length,
            return_tensors='pt'
        )

        input_ids = encodings['input_ids'].to(self.device)
        attention_mask = encodings['attention_mask'].to(self.device)

        # 批量预测
        with torch.no_grad():
            outputs = self.model.predict(input_ids, attention_mask, return_all_levels=True)

        batch_size = len(texts)
        for sample_idx in range(batch_size):
            predictions = []
            confidences = []
            full_path = []

            for level_idx in range(len(outputs['predictions'])):
                pred_idx = outputs['predictions'][level_idx][sample_idx].item()
                conf = outputs['confidences'][level_idx][sample_idx].item()

                if pred_idx < len(self.level_labels[level_idx]):
                    label = self.level_labels[level_idx][pred_idx]
                    predictions.append({
                        'level': level_idx,
                        'name': label,
                        'label': label,
                        'confidence': float(conf)
                    })
                    confidences.append(float(conf))
                    full_path.append(label)

            result = {
                'text': texts[sample_idx],
                'predictions': predictions if return_all_levels else predictions[-1:],
                'full_path': ' > '.join(full_path),
                'confidence_avg': sum(confidences) / len(confidences) if confidences else 0.0,
                'num_levels': len(predictions)
            }
            results.append(result)

        return results

    def predict_from_file(self, input_file: str, output_file: str = None,
                          text_column: str = 'text', batch_size: int = 32) -> pd.DataFrame:
        """
        从文件预测

        Args:
            input_file: 输入CSV文件
            output_file: 输出CSV文件
            text_column: 文本列名
            batch_size: 批处理大小

        Returns:
            结果DataFrame
        """
        print(f"读取文件: {input_file}")
        df = pd.read_csv(input_file)

        if text_column not in df.columns:
            raise ValueError(f"未找到列: {text_column}")

        texts = df[text_column].tolist()
        print(f"共 {len(texts)} 条文本")

        # 批量预测
        results = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_results = self.predict_batch(batch_texts)
            results.extend(batch_results)
            print(f"已处理: {min(i + batch_size, len(texts))}/{len(texts)}")

        # 构建结果DataFrame
        output_data = []
        for idx, result in enumerate(results):
            row = {
                'id': idx,
                'text': result['text'],
                'full_path': result['full_path'],
                'confidence_avg': result['confidence_avg'],
                'num_levels': result['num_levels']
            }

            # 添加各层级的预测结果
            for pred in result['predictions']:
                row[f"level{pred['level']}"] = pred['label']
                row[f"level{pred['level']}_confidence"] = pred['confidence']

            output_data.append(row)

        result_df = pd.DataFrame(output_data)

        # 保存结果
        if output_file is None:
            output_file = Path(input_file).stem + '_predicted.csv'

        result_df.to_csv(output_file, index=False)
        print(f"\n✅ 预测完成！结果已保存到: {output_file}")

        return result_df

    def interactive_mode(self):
        """交互式预测模式"""
        print("\n" + "="*50)
        print("交互式预测模式")
        print("="*50)
        print("输入文本进行预测，输入 'quit' 退出\n")

        while True:
            text = input("请输入文本: ").strip()

            if text.lower() in ['quit', 'exit', 'q']:
                print("退出交互模式")
                break

            if not text:
                continue

            result = self.predict_single(text)

            print(f"\n预测结果:")
            print(f"完整路径: {result['full_path']}")
            print(f"平均置信度: {result['confidence_avg']:.3f}")
            print(f"层级详情:")
            for pred in result['predictions']:
                print(f"  Level {pred['level']}: {pred['label']} (置信度: {pred['confidence']:.3f})")
            print()

    def print_model_info(self):
        """打印模型信息"""
        print("\n" + "="*50)
        print("模型信息")
        print("="*50)
        print(f"模型路径: {self.model_path}")
        print(f"层级数量: {self.hierarchy_config['num_levels']}")
        print(f"\n各层级信息:")
        for level_idx, labels in self.level_labels.items():
            print(f"  Level {level_idx}: {len(labels)} 个标签")
            if len(labels) <= 10:
                print(f"    标签: {', '.join(labels)}")
            else:
                print(f"    示例: {', '.join(labels[:5])} ... 等{len(labels)}个")
        print("="*50 + "\n")


def main():
    parser = argparse.ArgumentParser(description='动态层级BERT预测')
    parser.add_argument('--model_path', type=str, default='models_dynamic',
                        help='模型路径')
    parser.add_argument('--hierarchy_config', type=str, default='datasets/hierarchy_config.json',
                        help='层级配置文件路径')
    parser.add_argument('--label_mapping', type=str, default=None,
                        help='标签映射文件路径')
    parser.add_argument('--mode', type=str, default='interactive',
                        choices=['interactive', 'single', 'batch', 'file'],
                        help='预测模式')
    parser.add_argument('--text', type=str, default=None,
                        help='单条预测的文本')
    parser.add_argument('--input_file', type=str, default=None,
                        help='输入文件路径')
    parser.add_argument('--output_file', type=str, default=None,
                        help='输出文件路径')
    parser.add_argument('--text_column', type=str, default='text',
                        help='文本列名')
    parser.add_argument('--device', type=str, default='auto',
                        choices=['auto', 'cuda', 'cpu'],
                        help='设备')

    args = parser.parse_args()

    # 初始化预测器
    predictor = DynamicHierarchicalPredictor(
        model_path=args.model_path,
        hierarchy_config_path=args.hierarchy_config,
        label_mapping_path=args.label_mapping,
        device=args.device
    )

    # 打印模型信息
    predictor.print_model_info()

    # 根据模式执行预测
    if args.mode == 'interactive':
        predictor.interactive_mode()

    elif args.mode == 'single':
        if not args.text:
            print("错误: 单条模式需要 --text 参数")
            return

        result = predictor.predict_single(args.text)
        print(f"\n预测结果:")
        print(f"完整路径: {result['full_path']}")
        print(f"平均置信度: {result['confidence_avg']:.3f}")
        print(f"层级详情:")
        for pred in result['predictions']:
            print(f"  Level {pred['level']}: {pred['label']} (置信度: {pred['confidence']:.3f})")

    elif args.mode == 'file':
        if not args.input_file:
            print("错误: 文件模式需要 --input_file 参数")
            return

        predictor.predict_from_file(
            input_file=args.input_file,
            output_file=args.output_file,
            text_column=args.text_column
        )


if __name__ == "__main__":
    main()
