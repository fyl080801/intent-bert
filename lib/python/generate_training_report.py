#!/usr/bin/env python3
"""
训练报告生成器
生成直观的训练结果统计报告，并保存为文件
"""

import json
import os
import sys
from datetime import datetime


# 全局变量 - 用于累积报告内容
_report_lines = []


def print_header(text):
    """打印标题"""
    line = "\n" + "=" * 70
    content = f"  {text}"
    _report_lines.extend([line, content, "=" * 70])
    print(line)
    print(content)
    print("=" * 70)


def print_section(title):
    """打印小节标题"""
    line = f"\n{'━' * 70}"
    content = f"  {title}"
    end_line = f"{'━' * 70}"
    _report_lines.extend([line, content, end_line])
    print(line)
    print(content)
    print(end_line)


def print_table(headers, rows):
    """打印表格"""
    # 计算每列宽度
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(header)
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)

    # 打印表头
    header_line = "┌" + "┬".join("─" * w for w in col_widths) + "┐"
    header_content = "│" + "".join(f" {h:<{w-1}}│" for h, w in zip(headers, col_widths))
    separator = "├" + "┼".join("─" * w for w in col_widths) + "┤"

    # 表格内容
    row_contents = []
    for row in rows:
        row_content = "│"
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_content += f" {str(cell):<{col_widths[i]-1}}│"
        row_contents.append(row_content)

    # 底线
    bottom_line = "└" + "┴".join("─" * w for w in col_widths) + "┘"

    # 保存到列表并打印
    lines = [header_line, header_content, separator] + row_contents + [bottom_line]
    _report_lines.extend(lines)
    for line in lines:
        print(line)


def print_metric(label, value, unit=""):
    """打印单个指标"""
    if unit:
        line = f"  {label:<30} : {value:>15} {unit}"
    else:
        line = f"  {label:<30} : {value:>15}"
    _report_lines.append(line)
    print(line)


def print_custom(text):
    """打印自定义文本"""
    _report_lines.append(text)
    print(text)


def save_report_to_file(filepath):
    """将累积的报告内容保存到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(_report_lines))
        f.write('\n')


def generate_report(model_path, dataset_name):
    """生成训练报告"""

    # 清空之前的内容
    global _report_lines
    _report_lines = []

    # 报告文件路径
    report_file = os.path.join(model_path, "training_report.txt")
    print(f"\n📝 报告将保存到: {report_file}", file=sys.stdout)

    print_header("🎯 BERT模型训练报告")

    # 检查模型路径
    if not os.path.exists(model_path):
        print_custom(f"\n❌ 错误: 模型路径不存在: {model_path}")
        save_report_to_file(report_file)
        sys.exit(1)

    # 读取训练配置
    config_file = os.path.join(model_path, "training_config.json")
    if not os.path.exists(config_file):
        print_custom(f"\n❌ 错误: 训练配置文件不存在: {config_file}")
        save_report_to_file(report_file)
        sys.exit(1)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 基本信息
    print_section("📋 基本信息")
    print_metric("数据集名称", dataset_name)
    print_metric("任务类型", config.get("task_type", "N/A"))
    print_metric("标签类型", config.get("label_type", "N/A"))
    print_metric("模型名称", config.get("model_name", "N/A"))
    print_metric("模型版本", config.get("model_version", "N/A"))

    # 训练参数
    print_section("⚙️ 训练参数")
    print_metric("批次大小", config.get("batch_size", "N/A"))
    print_metric("训练轮数", config.get("num_epochs", "N/A"))
    print_metric("学习率", config.get("learning_rate", "N/A"))
    print_metric("最大序列长度", config.get("max_length", "N/A"))
    print_metric("Warmup步数", config.get("warmup_steps", "N/A"))
    print_metric("权重衰减", config.get("weight_decay", "N/A"))

    # 评估结果
    if "eval_results" in config and config["eval_results"]:
        print_section("📊 评估结果")

        eval_results = config["eval_results"]

        # 如果是多级标签，分别显示
        if any("_loss" in k for k in eval_results.keys()):
            # 多级标签结果
            levels = set()
            for key in eval_results.keys():
                if "_loss" in key or "_f1" in key or "_precision" in key or "_recall" in key:
                    level = key.split("_")[0]
                    levels.add(level)

            for level in sorted(levels):
                print_custom(f"\n  【Level {level.upper()}】")

                metrics = []
                for metric_type in ["loss", "f1", "precision", "recall"]:
                    key = f"{level}_{metric_type}"
                    if key in eval_results:
                        value = eval_results[key]
                        if metric_type in ["f1", "precision", "recall"]:
                            metrics.append([metric_type.upper(), f"{value:.4f}", "分数"])
                        else:
                            metrics.append([metric_type.upper(), f"{value:.4f}", ""])

                if metrics:
                    print_table(["指标", "值", "单位"], metrics)
        else:
            # 单标签/多标签结果
            metrics = []
            for key, value in eval_results.items():
                if isinstance(value, (int, float)):
                    if any(x in key.lower() for x in ["f1", "precision", "recall", "accuracy"]):
                        metrics.append([key.upper(), f"{value:.4f}", "分数"])
                    elif "loss" in key.lower():
                        metrics.append([key.upper(), f"{value:.4f}", ""])

            if metrics:
                print_table(["指标", "值", "单位"], metrics)

    # 模型文件信息
    print_section("💾 模型文件信息")

    model_files = []
    total_size = 0

    # 检查不同格式的模型文件
    if os.path.exists(os.path.join(model_path, "pytorch_model.bin")):
        size = os.path.getsize(os.path.join(model_path, "pytorch_model.bin")) / (1024 * 1024)
        model_files.append(["pytorch_model.bin", f"{size:.2f}", "MB"])
        total_size += size

    if os.path.exists(os.path.join(model_path, "model.safetensors")):
        size = os.path.getsize(os.path.join(model_path, "model.safetensors")) / (1024 * 1024)
        model_files.append(["model.safetensors", f"{size:.2f}", "MB"])
        total_size += size

    # 配置文件
    config_files = ["config.json", "training_config.json", "label_encoders.json"]
    for config_file_name in config_files:
        if os.path.exists(os.path.join(model_path, config_file_name)):
            size = os.path.getsize(os.path.join(model_path, config_file_name)) / 1024
            model_files.append([config_file_name, f"{size:.2f}", "KB"])

    # 其他文件
    for item in os.listdir(model_path):
        item_path = os.path.join(model_path, item)
        if os.path.isfile(item_path) and item not in [f[0] for f in model_files]:
            size = os.path.getsize(item_path) / 1024
            model_files.append([item, f"{size:.2f}", "KB"])

    if model_files:
        print_table(["文件名", "大小", "单位"], model_files)
        print_metric("\n  总大小", f"{total_size:.2f}", "MB")

    # 标签信息
    if "num_labels" in config or "num_labels_list" in config:
        print_section("🏷️ 标签信息")

        if "num_labels_list" in config:
            print_metric("标签类型", "多级标签")
            for i, num_labels in enumerate(config["num_labels_list"], 1):
                print_metric(f"  Level {i} 标签数", num_labels)
        else:
            print_metric("标签类型", "单标签/多标签")
            print_metric("标签总数", config.get("num_labels", "N/A"))

    # 训练完成信息
    completed_file = os.path.join(model_path, "training_completed.txt")
    if os.path.exists(completed_file):
        print_section("✅ 训练完成信息")

        with open(completed_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    print_metric(key.strip(), value.strip())

    # 输出路径
    print_section("📂 输出路径")
    print_custom(f"  容器内路径: {model_path}")
    print_custom(f"  工作流UID: {os.getenv('WORKFLOW_UID', 'N/A')}")

    # 总结
    print("\n" + "=" * 70)
    print("  📈 训练总结")
    print("=" * 70)
    _report_lines.extend(["\n" + "=" * 70, "  📈 训练总结", "=" * 70])

    if "eval_results" in config and config["eval_results"]:
        eval_results = config["eval_results"]

        # 尝试找到主要的评估指标
        summary_metrics = []

        if "eval_f1" in eval_results:
            summary_metrics.append(f"F1分数: {eval_results['eval_f1']:.2%}")
        if "eval_accuracy" in eval_results:
            summary_metrics.append(f"准确率: {eval_results['eval_accuracy']:.2%}")
        if "eval_loss" in eval_results:
            summary_metrics.append(f"损失: {eval_results['eval_loss']:.4f}")

        # 多级标签的总结
        for level in ["level1", "level2", "level3"]:
            if f"{level}_f1" in eval_results:
                f1_value = eval_results[f"{level}_f1"]
                summary_metrics.append(f"{level.upper()} F1: {f1_value:.2%}")

        if summary_metrics:
            print("  主要指标:")
            _report_lines.append("  主要指标:")
            for metric in summary_metrics:
                print(f"    • {metric}")
                _report_lines.append(f"    • {metric}")

    print(f"\n  模型已成功训练并保存到: {model_path}")
    print(f"  模型总大小: {total_size:.2f} MB")
    _report_lines.append(f"\n  模型已成功训练并保存到: {model_path}")
    _report_lines.append(f"  模型总大小: {total_size:.2f} MB")

    print("\n" + "=" * 70)
    print("  ✨ 训练完成！模型已就绪，可以用于推理部署")
    print("=" * 70 + "\n")
    _report_lines.extend(["\n" + "=" * 70, "  ✨ 训练完成！模型已就绪，可以用于推理部署", "=" * 70, "\n"])

    # 保存报告到文件
    save_report_to_file(report_file)

    # 显示保存确认（仅输出到控制台）
    print(f"\n✅ 报告已保存到: {report_file}")


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python generate_training_report.py <model_path> <dataset_name>")
        sys.exit(1)

    model_path = sys.argv[1]
    dataset_name = sys.argv[2]

    generate_report(model_path, dataset_name)


if __name__ == "__main__":
    main()
