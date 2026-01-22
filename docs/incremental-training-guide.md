# BERT 增量训练使用指南

## 概述

本指南说明如何使用增量训练功能，在已有模型基础上使用新数据进行微调，适合定期数据更新场景。

## 核心概念

### 什么是增量训练？

增量训练（Incremental Training）是指在已有训练好的模型基础上，使用新数据继续训练模型。相比从头训练，增量训练具有以下优势：

1. **训练更快** - 基于已有模型，收敛速度更快
2. **保留旧知识** - 结合旧数据采样，避免灾难性遗忘
3. **适应新数据** - 持续学习新的数据分布和类别

### 数据合并策略

系统支持三种数据合并策略：

| 策略 | 说明 | 适用场景 | 训练时间 |
|------|------|----------|----------|
| `new_only` | 仅使用新数据 | 快速适配新领域，旧数据可能过时 | 最短 |
| `sample` | 采样部分旧数据 + 新数据 | 平衡新旧知识，控制训练时间 | 适中 |
| `merge` | 全部旧数据 + 新数据 | 旧数据很重要，不能遗忘 | 最长 |

## 使用方法

### 方法 1: 本地增量训练（推荐用于测试）

#### 步骤 1: 准备数据

```bash
# 假设你有以下数据文件
datasets/
├── v1/
│   └── train.csv          # 旧数据（1000条）
└── v2/
    └── train.csv          # 新数据（200条）
```

#### 步骤 2: 准备增量训练数据

使用数据准备脚本合并新旧数据：

```bash
# 采样 30% 旧数据 + 新数据
python3 lib/python/prepare_incremental_data.py \
    --new_data datasets/v2/train.csv \
    --old_data datasets/v1/train.csv \
    --output datasets/incremental_train.csv \
    --strategy sample \
    --sample_ratio 0.3 \
    --random_seed 42 \
    --stats_output datasets/data_stats.json
```

输出示例：
```
======================================================================
增量训练数据准备
======================================================================

📂 读取新数据: datasets/v2/train.csv
  ✓ 新数据样本数: 200

📂 读取旧数据: datasets/v1/train.csv
  ✓ 旧数据样本数: 1000

📋 策略: 采样旧数据 (sample)
  采样比例: 30.0%
  采样数量: 300 / 1000

🔀 打乱数据顺序 (随机种子: 42)

💾 保存准备好的数据: datasets/incremental_train.csv

======================================================================
✅ 数据准备完成
======================================================================
总样本数: 500
  - 新数据: 200
  - 旧数据: 300 (可用: 1000)
策略: sample
采样比例: 30.0%
```

#### 步骤 3: 执行增量训练

```bash
# 使用准备好的数据进行增量训练
python3 lib/python/train_universal.py \
    --dataset financial_intent_fixed \
    --registry datasets/dataset_registry.json \
    --output_dir models/incremental_v2 \
    --base_model_path models/v1 \
    --num_epochs 3 \
    --learning_rate 1e-5  # 增量训练建议使用较小学习率
```

**注意**：你需要手动修改数据集配置文件，将训练数据路径指向准备好的数据：

```json
// datasets/dataset_registry.json
{
  "datasets": {
    "financial_intent_fixed": {
      "data_paths": {
        "train": "datasets/incremental_train.csv",  // 修改为准备好的数据
        "validation": "datasets/financial_intent_fixed/val.csv"
      }
    }
  }
}
```

### 方法 2: Argo Workflow 增量训练

由于 Argo Workflow 的配置复杂性，建议使用以下方法：

#### 方案 A: 修改数据集注册表

1. 为新版本数据创建新的数据集条目：

```json
{
  "datasets": {
    "financial_intent_fixed_v1": {
      "name": "金融意图分类 V1",
      "data_paths": {
        "train": "datasets/v1/train.csv",
        "validation": "datasets/financial_intent_fixed/val.csv"
      },
      ...
    },
    "financial_intent_fixed_v2": {
      "name": "金融意图分类 V2（增量）",
      "data_paths": {
        "train": "datasets/incremental_train.csv",  // 使用准备好的数据
        "validation": "datasets/financial_intent_fixed/val.csv"
      },
      ...
    }
  }
}
```

2. 先训练 V1 模型：
```bash
kubectl create -f <(argo submit \
  --name bert-training-v1 \
  --from argo-workflows/bert-training-universal.yaml \
  -p dataset_name="financial_intent_fixed_v1" \
  -p output_suffix="v1-001"
)
```

3. 准备增量数据后，训练 V2 模型：
```bash
# 先准备好增量数据
python3 lib/python/prepare_incremental_data.py \
    --new_data datasets/v2/train.csv \
    --old_data datasets/v1/train.csv \
    --output datasets/incremental_train.csv \
    --strategy sample \
    --sample_ratio 0.3

# 提交 V2 训练任务（需要手动指定基础模型路径）
kubectl create -f <(argo submit \
  --name bert-training-v2 \
  --from argo-workflows/bert-training-universal.yaml \
  -p dataset_name="financial_intent_fixed_v2" \
  -p output_suffix="v2-001" \
  -p model_name="/mnt/models/bert-output/financial_intent_fixed_v1-v1-001"  # 使用 V1 模型
)
```

**注意**：这需要修改训练脚本以支持 `model_name` 参数接受本地路径。

## 最佳实践

### 1. 学习率设置

增量训练时建议使用较小的学习率：

```bash
# 从头训练
--learning_rate 2e-5

# 增量训练
--learning_rate 1e-5  # 或 5e-6
```

### 2. 训练轮数

增量训练通常需要较少的轮数：

```bash
# 从头训练
--num_epochs 5

# 增量训练
--num_epochs 2-3  # 避免过拟合新数据
```

### 3. 数据采样比例

根据场景选择合适的采样比例：

| 场景 | 采样比例 | 理由 |
|------|----------|------|
| 新数据与旧数据相似 | 10-20% | 少量旧数据即可避免遗忘 |
| 新数据与旧数据差异大 | 40-50% | 需要更多旧数据保留原有知识 |
| 定期小规模更新 | 30% | 平衡训练时间和知识保留 |

### 4. 模型版本管理

建议使用时间戳或语义化版本号：

```
models/
├── financial_intent_20250122_v1.0.0/  # 初始模型
├── financial_intent_20250129_v1.1.0/  # 第一次增量更新
├── financial_intent_20250205_v1.2.0/  # 第二次增量更新
└── financial_intent_20250212_v2.0.0/  # 重大更新（新数据集）
```

### 5. 评估与对比

每次增量训练后，对比新旧模型的性能：

```bash
# 评估 V1 模型
python3 lib/python/predict.py \
    --model models/v1 \
    --test_data datasets/test.csv

# 评估 V2 模型
python3 lib/python/predict.py \
    --model models/v2 \
    --test_data datasets/test.csv
```

## 常见问题

### Q1: 增量训练后模型性能下降了怎么办？

**可能原因**：
- 新数据质量差
- 学习率过大导致遗忘
- 采样比例不合适

**解决方案**：
1. 检查新数据质量
2. 降低学习率（如 5e-6）
3. 增加旧数据采样比例
4. 使用更多训练轮数

### Q2: 如何判断是否需要增量训练？

**适合增量训练的场景**：
- ✅ 定期获得新标注数据（每周/每月）
- ✅ 新数据与旧数据同分布
- ✅ 需要保留旧知识
- ✅ 训练资源有限

**不适合增量训练的场景**：
- ❌ 数据分布发生重大变化
- ❌ 新增大量新类别
- ❌ 旧数据完全过时

### Q3: 能否跨任务类型增量训练？

**不能**。增量训练要求：
- 相同的任务类型（如都是层级分类）
- 兼容的标签空间（或接受重新初始化分类层）
- 相同的数据格式

### Q4: 如何处理新增标签？

如果新数据包含基础模型中不存在的标签：

```bash
# 训练脚本会自动检测并警告
⚠️  警告: 新数据的标签空间与基础模型不同
  基础模型: L1=6, L2=20, L3=50
  新数据: L1=7, L2=22, L3=55
  将使用新数据的标签空间重新初始化分类层
```

这会重新初始化分类层，但保留 BERT 层的预训练权重。

## 工作流示例

### 场景：每周更新模型

```bash
#!/bin/bash
# weekly_update.sh - 每周模型更新脚本

set -e

# 配置
DATASET_NAME="financial_intent_fixed"
OLD_DATA_VERSION="v$(date -d '1 week ago' +%Y%m%d)"
NEW_DATA_VERSION="v$(date +%Y%m%d)"
OLD_MODEL_PATH="/mnt/models/bert-output/${DATASET_NAME}_${OLD_DATA_VERSION}"
OUTPUT_SUFFIX="${NEW_DATA_VERSION}"

echo "=========================================="
echo "每周模型更新 - ${NEW_DATA_VERSION}"
echo "=========================================="

# 步骤 1: 准备增量数据
echo "步骤 1: 准备增量数据..."
python3 lib/python/prepare_incremental_data.py \
    --new_data "datasets/${NEW_DATA_VERSION}/train.csv" \
    --old_data "datasets/${OLD_DATA_VERSION}/train.csv" \
    --output "datasets/incremental_train.csv" \
    --strategy sample \
    --sample_ratio 0.3 \
    --random_seed 42

# 步骤 2: 更新数据集注册表
echo "步骤 2: 更新数据集注册表..."
python3 scripts/update_dataset_registry.py \
    --dataset ${DATASET_NAME} \
    --train_path "datasets/incremental_train.csv"

# 步骤 3: 提交训练任务
echo "步骤 3: 提交训练任务..."
kubectl create -f <(argo submit \
  --name bert-incremental-${NEW_DATA_VERSION} \
  --from argo-workflows/bert-training-universal.yaml \
  -p dataset_name="${DATASET_NAME}" \
  -p output_suffix="${OUTPUT_SUFFIX}" \
  -p model_name="${OLD_MODEL_PATH}" \
  -p num_epochs="3" \
  -p learning_rate="1e-5")

echo "=========================================="
echo "训练任务已提交"
echo "监控: kubectl get workflow -w"
echo "=========================================="
```

## 总结

增量训练是持续学习的关键技术，特别适合定期数据更新场景。通过合理设置数据采样比例、学习率和训练轮数，可以在保留旧知识的同时学习新数据，实现模型的持续优化。

关键要点：
1. ✅ 使用 `prepare_incremental_data.py` 准备训练数据
2. ✅ 选择合适的数据合并策略
3. ✅ 使用较小的学习率和较少的训练轮数
4. ✅ 定期评估模型性能
5. ✅ 做好模型版本管理

更多信息请参考：
- [数据集注册表配置](../datasets/dataset_registry.json)
- [训练脚本说明](../lib/python/train_universal.py)
- [数据准备脚本](../lib/python/prepare_incremental_data.py)
