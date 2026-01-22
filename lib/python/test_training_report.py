#!/usr/bin/env python3
"""
测试训练报告生成器
创建模拟数据并生成报告样例
"""

import os
import json
import tempfile
import shutil
from generate_training_report import generate_report


def create_mock_training_data(temp_dir):
    """创建模拟的训练数据"""

    # 创建 training_config.json
    training_config = {
        "model_name": "bert-base-chinese",
        "model_version": "v1",
        "task_type": "multi_label_classification",
        "label_type": "hierarchical",
        "batch_size": 16,
        "num_epochs": 5,
        "learning_rate": 2e-5,
        "max_length": 128,
        "warmup_steps": 500,
        "weight_decay": 0.01,
        "num_labels_list": [10, 25, 50],
        "eval_results": {
            "level1_loss": 0.1523,
            "level1_f1": 0.9234,
            "level1_precision": 0.9156,
            "level1_recall": 0.9312,
            "level2_loss": 0.2345,
            "level2_f1": 0.8765,
            "level2_precision": 0.8698,
            "level2_recall": 0.8834,
            "level3_loss": 0.3456,
            "level3_f1": 0.8234,
            "level3_precision": 0.8156,
            "level3_recall": 0.8312,
            "eval_loss": 0.7324,
            "eval_runtime": 15.23,
            "eval_samples_per_second": 65.66
        },
        "train_results": {
            "train_loss": 0.4523,
            "train_runtime": 1234.56,
            "train_samples_per_second": 78.34
        }
    }

    with open(os.path.join(temp_dir, "training_config.json"), 'w', encoding='utf-8') as f:
        json.dump(training_config, f, ensure_ascii=False, indent=2)

    # 创建 config.json
    config = {
        "architectures": ["BertForMultiLabelClassification"],
        "model_type": "bert",
        "num_labels_list": [10, 25, 50]
    }

    with open(os.path.join(temp_dir, "config.json"), 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 创建 label_encoders.json
    label_encoders = {
        "level1_labels": ["label1_1", "label1_2", "label1_3"],
        "level2_labels": ["label2_1", "label2_2"],
        "level3_labels": ["label3_1"]
    }

    with open(os.path.join(temp_dir, "label_encoders.json"), 'w', encoding='utf-8') as f:
        json.dump(label_encoders, f, ensure_ascii=False, indent=2)

    # 创建模拟的模型文件
    model_file = os.path.join(temp_dir, "pytorch_model.bin")
    with open(model_file, 'wb') as f:
        f.write(b'0' * (100 * 1024 * 1024))  # 100MB

    # 创建训练完成标记
    completed_file = os.path.join(temp_dir, "training_completed.txt")
    with open(completed_file, 'w', encoding='utf-8') as f:
        f.write("训练完成时间: 2026-01-22T10:30:45+08:00\n")
        f.write("工作流UID: test-workflow-uid-12345\n")
        f.write("数据集名称: financial_intent_fixed\n")
        f.write("宿主机保存路径: /mnt/models/bert-output/financial_intent_fixed-test-workflow-uid-12345\n")


def main():
    """主函数"""
    print("开始测试训练报告生成器...\n")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="bert_model_test_")

    try:
        # 创建模拟数据
        print(f"创建模拟训练数据到: {temp_dir}")
        create_mock_training_data(temp_dir)

        # 生成报告
        print("\n" + "=" * 70)
        print("生成训练报告样例")
        print("=" * 70 + "\n")

        dataset_name = "financial_intent_fixed"
        generate_report(temp_dir, dataset_name)

        print("\n✓ 报告生成测试完成！")

    finally:
        # 清理临时目录
        print(f"\n清理临时目录: {temp_dir}")
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
