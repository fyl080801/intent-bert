#!/usr/bin/env python3
"""
金融意图BERT模型推理脚本
支持单条预测和批量预测
"""

import os
import json
import argparse
import torch
from transformers import BertTokenizer
from models import BertForMultiLabelClassification
from typing import List, Dict, Union
import pandas as pd


class FinancialIntentPredictor:
    """金融意图预测器"""

    def __init__(self, model_path: str):
        """
        初始化预测器

        Args:
            model_path: 训练好的模型路径
        """
        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 加载标签编码器
        with open(os.path.join(model_path, 'label_encoders.json'), 'r', encoding='utf-8') as f:
            self.encoders = json.load(f)

        # 创建反向映射（编码 -> 标签）
        self.level1_id_to_label = {v: k for k, v in self.encoders['level1']['mapping'].items()}
        self.level2_id_to_label = {v: k for k, v in self.encoders['level2']['mapping'].items()}
        self.level3_id_to_label = {v: k for k, v in self.encoders['level3']['mapping'].items()}

        # 加载tokenizer
        self.tokenizer = BertTokenizer.from_pretrained(model_path)

        # 加载模型
        print(f"加载模型从: {model_path}")
        self.model = BertForMultiLabelClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
        print(f"模型已加载到设备: {self.device}")

        # 加载配置
        with open(os.path.join(model_path, 'training_config.json'), 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.max_length = self.config.get('max_length', 128)

    def predict_single(self, text: str) -> Dict[str, Union[str, float]]:
        """
        预测单条文本

        Args:
            text: 输入文本

        Returns:
            预测结果字典，包含标签和置信度
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        # 移到设备
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 预测
        with torch.no_grad():
            outputs = self.model(**inputs)

        # 提取logits
        logits_l1 = outputs['logits_level1'][0]
        logits_l2 = outputs['logits_level2'][0]
        logits_l3 = outputs['logits_level3'][0]

        # 获取预测和概率
        pred_l1 = torch.argmax(logits_l1).item()
        pred_l2 = torch.argmax(logits_l2).item()
        pred_l3 = torch.argmax(logits_l3).item()

        prob_l1 = torch.softmax(logits_l1, dim=0)[pred_l1].item()
        prob_l2 = torch.softmax(logits_l2, dim=0)[pred_l2].item()
        prob_l3 = torch.softmax(logits_l3, dim=0)[pred_l3].item()

        # 转换为标签
        return {
            'text': text,
            'label_level1': self.level1_id_to_label[pred_l1],
            'label_level2': self.level2_id_to_label[pred_l2],
            'label_level3': self.level3_id_to_label[pred_l3],
            'confidence_level1': prob_l1,
            'confidence_level2': prob_l2,
            'confidence_level3': prob_l3,
            'overall_confidence': (prob_l1 + prob_l2 + prob_l3) / 3
        }

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Union[str, float]]]:
        """
        批量预测

        Args:
            texts: 文本列表

        Returns:
            预测结果列表
        """
        results = []
        for text in texts:
            result = self.predict_single(text)
            results.append(result)
        return results

    def predict_from_file(self, input_file: str, output_file: str = None, text_column: str = 'text'):
        """
        从文件读取文本并预测

        Args:
            input_file: 输入CSV文件路径
            output_file: 输出CSV文件路径（可选）
            text_column: 文本列名
        """
        print(f"从文件加载数据: {input_file}")
        df = pd.read_csv(input_file)

        if text_column not in df.columns:
            raise ValueError(f"列 '{text_column}' 不在文件中。可用列: {df.columns.tolist()}")

        texts = df[text_column].tolist()
        print(f"预测 {len(texts)} 条数据...")

        results = self.predict_batch(texts)

        # 转换为DataFrame
        result_df = pd.DataFrame(results)

        # 合并原始数据
        output_df = pd.concat([df.reset_index(drop=True), result_df], axis=1)

        # 保存结果
        if output_file:
            output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"结果已保存到: {output_file}")

        return output_df


def main():
    parser = argparse.ArgumentParser(description='金融意图BERT模型推理')
    parser.add_argument('--model_path', type=str, default='models',
                        help='训练好的模型路径')
    parser.add_argument('--text', type=str, default=None,
                        help='要预测的文本')
    parser.add_argument('--input_file', type=str, default=None,
                        help='输入CSV文件路径')
    parser.add_argument('--output_file', type=str, default=None,
                        help='输出CSV文件路径')
    parser.add_argument('--text_column', type=str, default='text',
                        help='文本列名')
    parser.add_argument('--interactive', action='store_true',
                        help='交互式预测模式')

    args = parser.parse_args()

    # 创建预测器
    predictor = FinancialIntentPredictor(args.model_path)

    if args.interactive:
        # 交互式模式
        print("\n进入交互式预测模式（输入 'quit' 退出）")
        print("=" * 50)
        while True:
            text = input("\n请输入文本: ")
            if text.lower() in ['quit', 'exit', 'q']:
                print("退出交互模式")
                break

            if text.strip():
                result = predictor.predict_single(text)
                print("\n预测结果:")
                print(f"  一级标签: {result['label_level1']} (置信度: {result['confidence_level1']:.4f})")
                print(f"  二级标签: {result['label_level2']} (置信度: {result['confidence_level2']:.4f})")
                print(f"  三级标签: {result['label_level3']} (置信度: {result['confidence_level3']:.4f})")
                print(f"  整体置信度: {result['overall_confidence']:.4f}")

    elif args.text:
        # 单条预测
        result = predictor.predict_single(args.text)
        print("\n预测结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.input_file:
        # 文件批量预测
        result_df = predictor.predict_from_file(
            args.input_file,
            args.output_file,
            args.text_column
        )

        # 显示统计信息
        if args.output_file:
            print("\n预测完成！")
            print(f"总预测数: {len(result_df)}")

            # 标签分布统计
            print("\n一级标签分布:")
            print(result_df['label_level1'].value_counts())
            print("\n三级标签分布（前10）:")
            print(result_df['label_level3'].value_counts().head(10))

    else:
        # 显示示例
        print("\n未指定输入，使用示例文本进行预测")
        examples = [
            "基金怎么买",
            "我想申请贷款",
            "信用卡如何激活",
            "怎么转账",
            "理财产品的收益怎么样"
        ]

        print("\n示例预测:")
        print("=" * 50)
        for text in examples:
            result = predictor.predict_single(text)
            print(f"\n文本: {text}")
            print(f"  预测: {result['label_level1']} > {result['label_level2']} > {result['label_level3']}")
            print(f"  置信度: {result['overall_confidence']:.4f}")


if __name__ == '__main__':
    main()
