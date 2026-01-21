# BERT微调系统使用指南

本项目已经升级为支持多种标签类型的统一训练和推理系统。

## 主要特性

- ✅ **单标签分类**：情感分析、主题分类等
- ✅ **多标签分类**：多主题、多属性标注
- ✅ **多级标签分类**：固定层级和动态层级支持
- ✅ **参数化训练**：通过数据集名称一键训练
- ✅ **统一推理接口**：一致的API返回格式
- ✅ **Argo Workflow集成**：Kubernetes上的自动化训练

---

## 快速开始

### 1. 查看可用数据集

```bash
python3 lib/python/train_universal.py --list_datasets
```

输出：
```
可用的数据集:
============================================================
  - financial_intent_fixed: 金融意图分类（固定三级）
  - financial_intent_dynamic: 金融意图分类（动态多级）
  - jd_sentiment: 京东商品评论情感分析
============================================================
```

### 2. 验证数据集

```bash
# 验证所有数据集
python3 lib/python/validate_dataset.py

# 验证单个数据集
python3 lib/python/validate_dataset.py --dataset financial_intent_fixed
```

### 3. 训练模型

```bash
# 使用默认参数训练
python3 lib/python/train_universal.py --dataset financial_intent_fixed

# 自定义训练参数
python3 lib/python/train_universal.py \
  --dataset financial_intent_fixed \
  --batch_size 32 \
  --num_epochs 10 \
  --learning_rate 3e-5 \
  --output_dir models/my_model
```

### 4. 启动推理服务

```bash
# 使用新的统一推理服务
export MODEL_PATH=models/financial_intent_fixed
python3 lib/python/model_server_v2.py
```

### 5. 测试推理

```bash
# 单标签预测
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "这个产品质量很好"}'

# 多级标签预测
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "如何购买开放式基金"}'
```

---

## Argo Workflow使用

### 提交训练工作流

```bash
# 提交固定层级金融意图分类训练
kubectl create -f argo-workflows/bert-training-universal.yaml

# 或者使用argo CLI提交
argo submit argo-workflows/bert-training-universal.yaml \
  --parameter dataset_name=financial_intent_fixed \
  --parameter batch_size=32 \
  --parameter num_epochs=10
```

### 工作流参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `dataset_name` | 数据集名称（必需） | - |
| `model_name` | 预训练模型 | （使用数据集配置） |
| `batch_size` | 批次大小 | （使用数据集配置） |
| `num_epochs` | 训练轮数 | （使用数据集配置） |
| `learning_rate` | 学习率 | （使用数据集配置） |
| `model_version` | 动态模型版本 | v1 |

---

## API返回格式

### 单标签分类

```json
{
  "task_type": "single_label",
  "prediction": {
    "label": "positive",
    "label_id": 1,
    "confidence": 0.95
  },
  "all_probabilities": [
    {"label": "negative", "probability": 0.05},
    {"label": "positive", "probability": 0.95}
  ]
}
```

### 多级标签分类

```json
{
  "task_type": "hierarchical",
  "num_levels": 3,
  "prediction": [
    {
      "level": 1,
      "label": "投资理财",
      "label_id": 0,
      "confidence": 0.95
    },
    {
      "level": 2,
      "label": "基金投资",
      "label_id": 1,
      "confidence": 0.92
    },
    {
      "level": 3,
      "label": "开放式基金",
      "label_id": 3,
      "confidence": 0.88
    }
  ],
  "overall_confidence": 0.92
}
```

---

## 添加新数据集

### 1. 准备数据文件

```bash
mkdir -p datasets/my_dataset
# 准备 train.csv 和 dev.csv
```

### 2. 在注册表中添加配置

编辑 `datasets/dataset_registry.json`：

```json
{
  "datasets": {
    "my_dataset": {
      "name": "我的数据集",
      "task_type": "single_label",
      "label_type": "single_label",
      "data_paths": {
        "train": "datasets/my_dataset/train.csv",
        "validation": "datasets/my_dataset/dev.csv"
      },
      "text_column": "text",
      "label_columns": ["label"],
      "num_labels": 5,
      "training_script": "train_single_label.py",
      "model_class": "BertForSingleLabelClassification"
    }
  }
}
```

### 3. 验证和训练

```bash
# 验证
python3 lib/python/validate_dataset.py --dataset my_dataset

# 训练
python3 lib/python/train_universal.py --dataset my_dataset
```

---

## 文件结构

```
bert-aliyun-test/
├── datasets/
│   ├── dataset_registry.json          # 数据集注册表（新）
│   ├── hierarchy_config.json          # 动态层级配置
│   ├── financial_intent_dataset.csv   # 固定层级数据
│   └── jd/                            # 单标签数据集
│       ├── train.csv
│       └── dev.csv
├── lib/python/
│   ├── train_universal.py             # 通用训练脚本（新）
│   ├── model_server_v2.py             # 统一推理服务（新）
│   ├── validate_dataset.py            # 数据集验证（新）
│   ├── train.py                       # 固定层级训练
│   ├── train_dynamic.py               # 动态层级训练
│   ├── models.py                      # 固定层级模型
│   ├── dynamic_models.py              # 动态层级模型
│   └── hierarchy_config.py            # 层级配置解析
├── argo-workflows/
│   ├── bert-training-and-deployment.yaml  # 原工作流
│   └── bert-training-universal.yaml       # 新工作流（新）
└── docs/
    ├── DATASET_SPEC.md                # 数据集规范（新）
    └── UNIFIED_TRAINING_GUIDE.md      # 本文档
```

---

## 数据集类型对比

| 特性 | 单标签 | 多标签 | 多级标签 |
|------|--------|--------|----------|
| 标签数量 | 1个 | 0-N个 | N个（每层1个） |
| CSV格式 | `text,label` | `text,labels` | `text,l1,l2,l3,...` |
| 使用场景 | 情感分析 | 多主题分类 | 层级分类 |
| 训练脚本 | `train_single_label.py` | (TODO) | `train.py` 或 `train_dynamic.py` |
| 模型类 | `AutoModelForSequenceClassification` | (TODO) | `BertForMultiLabelClassification` |
| 层级配置 | 固定 | 固定 | 固定或动态 |

---

## 常见问题

### Q: 如何选择使用固定层级还是动态层级？

A:
- **固定层级**：所有样本都有相同数量的层级（如都是3级）
- **动态层级**：不同样本的层级数量不同（如有些2级，有些4级）

### Q: 推理服务如何同时支持多种模型？

A: `model_server_v2.py` 会自动加载模型的 `training_config.json`，识别任务类型并使用相应的预测逻辑。

### Q: 如何在Kubernetes上部署推理服务？

A:
1. 训练完成后，模型保存在 `/mnt/models/bert-output/`
2. 更新Deployment的 `MODEL_PATH` 环境变量指向模型目录
3. 使用 `model_server_v2.py` 作为服务入口

---

## 相关文档

- [数据集规范文档](DATASET_SPEC.md)
- [项目README](../CLAUDE.md)

---

**最后更新**: 2026-01-21
