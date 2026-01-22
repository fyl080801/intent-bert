# 增量训练示例

本指南展示如何使用拆分好的数据集进行增量训练。

## 数据集说明

已将 `financial_intent_fixed` 数据集拆分成两个版本：

- **V1 版本** (`financial_intent_incremental_v1`)
  - 训练集：999 条
  - 验证集：300 条
  - 用途：初始训练，建立基础模型

- **V2 版本** (`financial_intent_incremental_v2`)
  - 训练集：1,001 条
  - 验证集：300 条
  - 用途：增量训练，在 V1 模型基础上继续训练

数据集采用分层抽样，确保 6 个一级类别的分布均衡：
- 交易服务
- 产品咨询
- 信贷服务
- 投资理财
- 账户服务
- 风险合规

## 快速开始

### 步骤 1: 训练 V1 模型（初始训练）

```bash
python3 lib/python/train_universal.py \
  --dataset financial_intent_incremental_v1 \
  --registry datasets/dataset_registry.json \
  --output_dir models/incremental_v1 \
  --num_epochs 5 \
  --learning_rate 2e-5 \
  --batch_size 16
```

**输出：**
- 模型保存在：`models/incremental_v1/`
- 包含：`pytorch_model.bin`, `config.json`, `label_encoders.json`, `training_config.json`

### 步骤 2: 准备增量训练数据

使用 V2 数据 + 采样部分 V1 数据：

```bash
python3 lib/python/prepare_incremental_data.py \
  --new_data datasets/financial_intent_incremental_v2/train.csv \
  --old_data datasets/financial_intent_incremental_v1/train.csv \
  --output datasets/incremental_train_merged.csv \
  --strategy sample \
  --sample_ratio 0.3 \
  --random_seed 42 \
  --stats_output datasets/incremental_stats.json
```

**输出示例：**
```
总样本数: 1301
  - 新数据: 1001
  - 旧数据: 300 (采样 30%)
策略: sample
```

### 步骤 3: 训练 V2 模型（增量训练）

**重要：** 由于 `train_universal.py` 需要从数据集注册表读取路径，你有两个选择：

#### 选项 A: 创建临时数据集条目（推荐）

编辑 `datasets/dataset_registry.json`，添加一个新条目：

```json
"financial_intent_incremental_v2_merged": {
  "name": "金融意图增量训练 V2（合并数据）",
  "task_type": "hierarchical",
  "label_type": "multi_level",
  "level_config": "fixed",
  "num_levels": 3,
  "data_paths": {
    "train": "datasets/incremental_train_merged.csv",
    "validation": "datasets/financial_intent_incremental_v2/val.csv"
  },
  "config_path": "datasets/financial_intent_fixed/config.json",
  "label_columns": ["label_level1", "label_level2", "label_level3"],
  "text_column": "text",
  "training_script": "train.py",
  "model_class": "BertForMultiLabelClassification",
  "description": "增量训练V2版本 - 合并数据集（1001新+300旧）"
}
```

然后执行增量训练：

```bash
python3 lib/python/train_universal.py \
  --dataset financial_intent_incremental_v2_merged \
  --registry datasets/dataset_registry.json \
  --output_dir models/incremental_v2 \
  --base_model_path models/incremental_v1 \
  --num_epochs 3 \
  --learning_rate 1e-5 \
  --batch_size 16
```

#### 选项 B: 直接使用 train.py（不使用数据集注册表）

```bash
python3 lib/python/train.py \
  --train_data datasets/incremental_train_merged.csv \
  --val_data datasets/financial_intent_incremental_v2/val.csv \
  --model_name models/incremental_v1 \
  --output_dir models/incremental_v2 \
  --num_epochs 3 \
  --learning_rate 1e-5 \
  --batch_size 16
```

### 步骤 4: 对比模型性能

```bash
# 评估 V1 模型
python3 lib/python/predict.py \
  --model models/incremental_v1 \
  --test_data datasets/financial_intent_incremental_v2/val.csv

# 评估 V2 模型
python3 lib/python/predict.py \
  --model models/incremental_v2 \
  --test_data datasets/financial_intent_incremental_v2/val.csv
```

## 不同数据合并策略对比

### 策略 1: 仅新数据（new_only）

```bash
python3 lib/python/prepare_incremental_data.py \
  --new_data datasets/financial_intent_incremental_v2/train.csv \
  --old_data datasets/financial_intent_incremental_v1/train.csv \
  --output datasets/incremental_new_only.csv \
  --strategy new_only
```

**特点：**
- 训练最快
- 可能遗忘旧知识
- 适合：数据分布变化大，旧数据过时

### 策略 2: 采样旧数据（sample）- 推荐

```bash
python3 lib/python/prepare_incremental_data.py \
  --new_data datasets/financial_intent_incremental_v2/train.csv \
  --old_data datasets/financial_intent_incremental_v1/train.csv \
  --output datasets/incremental_sample.csv \
  --strategy sample \
  --sample_ratio 0.3
```

**特点：**
- 平衡新旧知识
- 训练时间适中
- 适合：定期数据更新

### 策略 3: 合并全部数据（merge）

```bash
python3 lib/python/prepare_incremental_data.py \
  --new_data datasets/financial_intent_incremental_v2/train.csv \
  --old_data datasets/financial_intent_incremental_v1/train.csv \
  --output datasets/incremental_merge.csv \
  --strategy merge
```

**特点：**
- 保留最多知识
- 训练时间最长
- 适合：旧数据很重要，不能遗忘

## 完整训练脚本示例

创建一个自动化脚本 `run_incremental_training.sh`：

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "增量训练流程"
echo "=========================================="

# 配置
V1_DATASET="financial_intent_incremental_v1"
V2_DATASET="financial_intent_incremental_v2"
V1_MODEL_DIR="models/incremental_v1"
V2_MODEL_DIR="models/incremental_v2"
SAMPLE_RATIO=0.3

# 步骤 1: 训练 V1 模型
echo ""
echo "步骤 1: 训练 V1 模型（初始训练）..."
python3 lib/python/train_universal.py \
  --dataset $V1_DATASET \
  --registry datasets/dataset_registry.json \
  --output_dir $V1_MODEL_DIR \
  --num_epochs 5 \
  --learning_rate 2e-5

# 步骤 2: 准备增量数据
echo ""
echo "步骤 2: 准备增量训练数据..."
python3 lib/python/prepare_incremental_data.py \
  --new_data datasets/financial_intent_incremental_v2/train.csv \
  --old_data datasets/financial_intent_incremental_v1/train.csv \
  --output datasets/incremental_train.csv \
  --strategy sample \
  --sample_ratio $SAMPLE_RATIO

# 步骤 3: 训练 V2 模型
echo ""
echo "步骤 3: 训练 V2 模型（增量训练）..."
python3 lib/python/train.py \
  --train_data datasets/incremental_train.csv \
  --val_data datasets/financial_intent_incremental_v2/val.csv \
  --model_name $V1_MODEL_DIR \
  --output_dir $V2_MODEL_DIR \
  --num_epochs 3 \
  --learning_rate 1e-5

# 步骤 4: 评估对比
echo ""
echo "步骤 4: 评估模型性能..."
echo "V1 模型评估结果："
# (添加评估命令)

echo ""
echo "V2 模型评估结果："
# (添加评估命令)

echo ""
echo "=========================================="
echo "增量训练完成！"
echo "=========================================="
echo "V1 模型: $V1_MODEL_DIR"
echo "V2 模型: $V2_MODEL_DIR"
```

运行：

```bash
chmod +x run_incremental_training.sh
./run_incremental_training.sh
```

## 数据集统计

查看详细的拆分统计信息：

```bash
cat datasets/split_stats.json | python3 -m json.tool
```

示例输出：

```json
{
  "total_samples": 2000,
  "v1_samples": 999,
  "v2_samples": 1001,
  "split_ratio": 0.5,
  "stratify_column": "label_level1",
  "random_seed": 42,
  "label_distribution": {
    "交易服务": {
      "total": 306,
      "v1": 153,
      "v2": 145
    },
    "产品咨询": {
      "total": 288,
      "v1": 144,
      "v2": 146
    },
    ...
  }
}
```

## Argo Workflow 使用

如果要在 Kubernetes 上运行，使用以下命令：

### 训练 V1 模型

```bash
kubectl create -f <(argo submit \
  --name bert-incremental-v1 \
  --from argo-workflows/bert-training-universal.yaml \
  -p dataset_name="financial_intent_incremental_v1" \
  -p output_suffix="inc-v1-001" \
  -p num_epochs="5" \
  -p learning_rate="2e-5")
```

### 训练 V2 模型

需要先准备好数据，然后：

```bash
kubectl create -f <(argo submit \
  --name bert-incremental-v2 \
  --from argo-workflows/bert-training-universal.yaml \
  -p dataset_name="financial_intent_incremental_v2" \
  -p output_suffix="inc-v2-001" \
  -p model_name="/mnt/models/bert-output/..." \
  -p num_epochs="3" \
  -p learning_rate="1e-5")
```

## 总结

增量训练的关键步骤：

1. ✅ 训练初始模型（V1）
2. ✅ 准备增量数据（合并新旧数据）
3. ✅ 增量训练（基于 V1 模型）
4. ✅ 评估对比

优势：
- 训练更快（基于已有模型）
- 保留旧知识（通过数据采样）
- 适应新数据（持续学习）
- 资源消耗更少（更少的训练轮数）
