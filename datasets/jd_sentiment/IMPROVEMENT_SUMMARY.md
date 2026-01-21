# BERT微调系统改进汇总

## 概述

本次改进将现有的BERT微调系统升级为支持多种标签类型的统一训练和推理平台。

---

## 改进内容

### 1. 数据集注册表 ✅

**文件**: `datasets/dataset_registry.json`

**功能**:
- 统一管理所有数据集的元信息
- 声明数据集类型（单标签/多标签/多级标签）
- 配置训练脚本和模型类型
- 支持参数化访问

**已注册数据集**:
- `financial_intent_fixed`: 固定三级金融意图分类
- `financial_intent_dynamic`: 动态多级金融意图分类
- `jd_sentiment`: 京东评论情感二分类

---

### 2. 数据集验证工具 ✅

**文件**: `lib/python/validate_dataset.py`

**功能**:
- 验证数据集格式是否符合规范
- 检查必需列和标签一致性
- 验证配置文件格式
- 支持批量验证所有数据集

**使用方法**:
```bash
# 验证所有数据集
python3 lib/python/validate_dataset.py

# 验证单个数据集
python3 lib/python/validate_dataset.py --dataset financial_intent_fixed
```

---

### 3. 通用训练脚本 ✅

**文件**: `lib/python/train_universal.py`

**功能**:
- 根据数据集名称自动选择训练方式
- 支持单标签、多标签、多级标签训练
- 自动加载对应的模型和训练脚本
- 统一的命令行接口

**使用方法**:
```bash
# 列出可用数据集
python3 lib/python/train_universal.py --list_datasets

# 训练指定数据集
python3 lib/python/train_universal.py --dataset financial_intent_fixed

# 自定义训练参数
python3 lib/python/train_universal.py \
  --dataset financial_intent_dynamic \
  --batch_size 32 \
  --num_epochs 10 \
  --model_version v2
```

**支持的任务类型**:
| 任务类型 | 训练脚本 | 模型类 |
|---------|---------|--------|
| 固定层级 | `train.py` | `BertForMultiLabelClassification` |
| 动态层级 | `train_dynamic.py` | `BertForDynamicHierarchicalClassification` |
| 单标签 | `train_single_label.py` | `AutoModelForSequenceClassification` |

---

### 4. 统一推理服务 ✅

**文件**: `lib/python/model_server_v2.py`

**功能**:
- 自动识别模型任务类型
- 统一的预测API接口
- 标准化的返回格式
- 支持单标签和层级标签预测

**API端点**:
- `POST /predict`: 单条预测
- `POST /predict_batch`: 批量预测
- `GET /model_info`: 模型信息
- `GET /health`: 健康检查

**返回格式示例**:

单标签分类:
```json
{
  "task_type": "single_label",
  "prediction": {
    "label": "positive",
    "label_id": 1,
    "confidence": 0.95
  },
  "all_probabilities": [...]
}
```

层级分类:
```json
{
  "task_type": "hierarchical",
  "num_levels": 3,
  "prediction": [
    {"level": 1, "label": "投资理财", "confidence": 0.95},
    {"level": 2, "label": "基金投资", "confidence": 0.92},
    {"level": 3, "label": "开放式基金", "confidence": 0.88}
  ],
  "overall_confidence": 0.92
}
```

---

### 5. 参数化Argo Workflow ✅

**文件**: `argo-workflows/bert-training-universal.yaml`

**功能**:
- 通过 `dataset_name` 参数选择数据集
- 自动解析数据集配置
- 支持训练参数覆盖
- 灵活的工作流配置

**核心参数**:
| 参数 | 说明 | 必需 |
|------|------|------|
| `dataset_name` | 数据集名称 | ✅ |
| `model_name` | 预训练模型 | ❌ |
| `batch_size` | 批次大小 | ❌ |
| `num_epochs` | 训练轮数 | ❌ |
| `learning_rate` | 学习率 | ❌ |
| `model_version` | 动态模型版本 | ❌ |

**使用方法**:
```bash
# 提交工作流
kubectl create -f argo-workflows/bert-training-universal.yaml

# 使用argo CLI提交并指定参数
argo submit argo-workflows/bert-training-universal.yaml \
  --parameter dataset_name=financial_intent_fixed \
  --parameter batch_size=32
```

---

### 6. 数据集规范文档 ✅

**文件**: `docs/DATASET_SPEC.md`

**内容**:
- 数据集类型定义
- CSV格式规范
- 配置文件规范
- 验证规则
- 最佳实践

**支持的数据集类型**:
1. **单标签分类** (single_label)
   - 一个文本列，一个标签列
   - 适用于：情感分析、主题分类

2. **多标签分类** (multi_label)
   - 一个文本列，标签为数组
   - 适用于：多主题分类

3. **层级分类** (hierarchical)
   - 一个文本列，多个层级标签列
   - 支持固定层级和动态层级
   - 适用于：具有分类体系的知识领域

---

### 7. 使用指南文档 ✅

**文件**: `docs/UNIFIED_TRAINING_GUIDE.md`

**内容**:
- 快速开始指南
- API使用示例
- 添加新数据集流程
- 常见问题解答
- 文件结构说明

---

## 数据集格式规范

### 单标签数据集

```csv
sentence,label,dataset
这个产品质量很好,1,jd
太差了，不推荐,0,jd
```

**配置**:
```json
{
  "task_type": "single_label",
  "label_type": "single_label",
  "text_column": "sentence",
  "label_columns": ["label"],
  "num_labels": 2
}
```

### 固定层级数据集

```csv
id,text,label_level1,label_level2,label_level3
1,如何购买开放式基金,投资理财,基金投资,开放式基金
2,查询股票持仓,投资理财,股票投资,持仓分析
```

**配置**:
```json
{
  "task_type": "hierarchical",
  "label_type": "multi_level",
  "level_config": "fixed",
  "num_levels": 3,
  "text_column": "text",
  "label_columns": ["label_level1", "label_level2", "label_level3"]
}
```

### 动态层级数据集

```csv
id,text,label_level1,label_level2,label_level3,label_level4
1,一级类别,投资理财,,,,
2,二级路径,投资理财,基金投资,,,
3,三级路径,投资理财,基金投资,开放式基金,
4,四级路径,投资理财,基金投资,开放式基金,申购
```

**配置**:
```json
{
  "task_type": "hierarchical",
  "level_config": "dynamic",
  "config_path": "datasets/hierarchy_config.json"
}
```

---

## 使用流程

### 添加新数据集

1. **准备数据文件**
   ```bash
   mkdir -p datasets/my_dataset
   # 准备 train.csv 和 dev.csv
   ```

2. **在注册表中添加配置**
   ```json
   {
     "datasets": {
       "my_dataset": {
         "name": "我的数据集",
         "task_type": "single_label",
         "data_paths": {
           "train": "datasets/my_dataset/train.csv",
           "validation": "datasets/my_dataset/dev.csv"
         },
         "text_column": "text",
         "label_columns": ["label"],
         "training_script": "train_single_label.py"
       }
     }
   }
   ```

3. **验证数据集**
   ```bash
   python3 lib/python/validate_dataset.py --dataset my_dataset
   ```

4. **训练模型**
   ```bash
   python3 lib/python/train_universal.py --dataset my_dataset
   ```

5. **在Workflow中使用**
   ```bash
   argo submit argo-workflows/bert-training-universal.yaml \
     --parameter dataset_name=my_dataset
   ```

---

## 文件变更汇总

### 新增文件

| 文件 | 说明 |
|------|------|
| `datasets/dataset_registry.json` | 数据集注册表 |
| `lib/python/validate_dataset.py` | 数据集验证工具 |
| `lib/python/train_universal.py` | 通用训练脚本 |
| `lib/python/model_server_v2.py` | 统一推理服务 |
| `argo-workflows/bert-training-universal.yaml` | 参数化工作流 |
| `docs/DATASET_SPEC.md` | 数据集规范文档 |
| `docs/UNIFIED_TRAINING_GUIDE.md` | 使用指南文档 |

### 保留文件（原有功能）

| 文件 | 说明 |
|------|------|
| `lib/python/train.py` | 固定层级训练（保留） |
| `lib/python/train_dynamic.py` | 动态层级训练（保留） |
| `lib/python/model_server.py` | 原推理服务（保留） |
| `argo-workflows/bert-training-and-deployment.yaml` | 原工作流（保留） |

---

## 技术亮点

1. **参数化设计**: 通过数据集名称一键训练，无需修改代码
2. **类型自动识别**: 推理服务自动识别模型类型
3. **统一接口**: 不同任务类型使用相同的API接口
4. **灵活扩展**: 轻松添加新的数据集和任务类型
5. **完整验证**: 内置数据集格式验证工具
6. **文档完善**: 详细的规范文档和使用指南

---

## 向后兼容性

- ✅ 原有的训练脚本继续可用
- ✅ 原有的推理服务继续可用
- ✅ 原有的Argo Workflow继续可用
- ✅ 新增功能不影响现有功能

---

## 下一步计划

1. **多标签分类**: 完善多标签训练和推理
2. **模型对比**: 添加不同数据集的模型性能对比
3. **自动超参优化**: 集成超参数搜索
4. **模型压缩**: 支持模型量化和蒸馏
5. **A/B测试**: 支持模型版本管理和A/B测试

---

**文档版本**: 1.0
**更新日期**: 2026-01-21
**作者**: Claude Code
