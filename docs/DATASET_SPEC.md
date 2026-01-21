# 数据集规范文档

本文档定义了BERT微调项目中数据集的标准格式和验证规范。

## 目录

- [概述](#概述)
- [数据集类型](#数据集类型)
- [数据集注册表](#数据集注册表)
- [数据集格式规范](#数据集格式规范)
- [配置文件规范](#配置文件规范)
- [数据集验证](#数据集验证)
- [使用示例](#使用示例)

---

## 概述

本项目支持三种类型的数据集：
- **单标签分类**：每个样本属于一个类别
- **多标签分类**：每个样本可属于多个类别
- **层级分类**：标签具有层级结构（固定或动态层级）

所有数据集必须在 `datasets/dataset_registry.json` 中注册，遵循统一的格式规范。

---

## 数据集类型

### 1. 单标签分类 (single_label)

每个样本只属于一个类别。

**特点**：
- 一个文本列
- 一个标签列
- 适用于情感分析、主题分类等任务

**示例场景**：京东评论情感分类（正面/负面）

### 2. 多标签分类 (multi_label)

每个样本可以同时属于多个类别。

**特点**：
- 一个文本列
- 标签可以是列表或JSON数组
- 适用于多主题分类、多属性标注等任务

**示例场景**：新闻多标签分类（体育+国际+足球）

### 3. 层级分类 (hierarchical)

标签具有层级关系，每个层级一个标签。

**特点**：
- 一个文本列
- 多个标签列（label_level1, label_level2, ...）
- 支持固定层级或动态层级
- 适用于具有明确分类体系的知识领域

**示例场景**：金融意图分类（投资理财 > 基金投资 > 开放式基金）

---

## 数据集注册表

### 注册表结构

数据集注册表位于 `datasets/dataset_registry.json`，定义所有可用数据集的元信息。

**必需字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 数据集显示名称 |
| `task_type` | string | 任务类型：single_label, multi_label, hierarchical |
| `label_type` | string | 标签类型：single_label, multi_label, multi_level |
| `data_paths.train` | string | 训练数据路径 |
| `data_paths.validation` | string | 验证数据路径 |
| `text_column` | string | 文本列名 |
| `label_columns` | array | 标签列名列表 |
| `training_script` | string | 使用的训练脚本 |
| `model_class` | string | 模型类名 |

**可选字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `config_path` | string | 配置文件路径（层级分类需要） |
| `num_levels` | int | 层级数量（层级分类） |
| `num_labels` | int | 标签数量（单/多标签分类） |
| `label_names` | array | 标签名称列表 |
| `level_config` | string | fixed 或 dynamic |
| `description` | string | 数据集描述 |
| `languages` | array | 支持的语言 |

### 已注册数据集

#### 1. financial_intent_fixed
固定三级金融意图分类
```json
{
  "task_type": "hierarchical",
  "num_levels": 3,
  "training_script": "train.py",
  "data_paths": {
    "train": "datasets/financial_intent_dataset.csv",
    "validation": "datasets/financial_intent_validation.csv"
  }
}
```

#### 2. financial_intent_dynamic
动态多级金融意图分类
```json
{
  "task_type": "hierarchical",
  "level_config": "dynamic",
  "training_script": "train_dynamic.py",
  "config_path": "datasets/hierarchy_config.json"
}
```

#### 3. jd_sentiment
京东商品评论情感分类
```json
{
  "task_type": "single_label",
  "num_labels": 2,
  "label_names": ["negative", "positive"],
  "training_script": "train_single_label.py"
}
```

---

## 数据集格式规范

### 单标签数据集格式

**CSV文件格式**：

```csv
id,text,label
1,这个产品质量很好,1
2,太差了，不推荐,0
```

**必需列**：
- `text` (或自定义名称): 文本内容
- `label` (或自定义名称): 整数或字符串标签

**可选列**：
- `id`: 唯一标识符
- `metadata`: 其他元数据

**数据集配置示例**：
```json
{
  "text_column": "sentence",
  "label_columns": ["label"],
  "num_labels": 2
}
```

### 多标签数据集格式

**CSV文件格式（JSON数组）**：

```csv
id,text,labels
1,这是一篇关于体育和国际新闻的文章,"[1, 5, 8]"
2,科技新闻,"[2]"
```

**必需列**：
- `text`: 文本内容
- `labels`: JSON数组格式的标签列表

**数据集配置示例**：
```json
{
  "text_column": "text",
  "label_columns": ["labels"],
  "num_labels": 10
}
```

### 层级分类数据集格式

#### 固定层级格式

**CSV文件格式**：

```csv
id,text,label_level1,label_level2,label_level3
1,如何购买开放式基金,投资理财,基金投资,开放式基金
2,查询股票持仓,投资理财,股票投资,持仓分析
3,转账汇款,交易服务,转账汇款,行内转账
```

**必需列**：
- `text`: 文本内容
- `label_level1`, `label_level2`, ..., `label_levelN`: 各层级标签

**规则**：
- 如果父级标签为空，子级标签也必须为空
- 所有完整路径应到达同一层级

**数据集配置示例**：
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

#### 动态层级格式

**CSV文件格式**（与固定层级相同，但深度可变）：

```csv
id,text,label_level1,label_level2,label_level3,label_level4
1,一级类别,投资理财,,,,
2,二级路径,投资理财,基金投资,,,
3,三级路径,投资理财,基金投资,开放式基金,
4,四级路径,投资理财,基金投资,开放式基金,申购
```

**规则**：
- 不同样本可以有不同深度
- 父级为空时，子级必须为空

**数据集配置示例**：
```json
{
  "task_type": "hierarchical",
  "level_config": "dynamic",
  "config_path": "datasets/hierarchy_config.json"
}
```

---

## 配置文件规范

### 层级配置文件 (hierarchy_config.json)

用于动态层级分类，定义标签的树形结构。

**格式**：

```json
{
  "version": "1.0",
  "description": "层级配置描述",
  "labels": [
    {
      "name": "一级标签",
      "children": [
        {
          "name": "二级标签",
          "children": [
            {"name": "三级标签", "children": []}
          ]
        }
      ]
    }
  ]
}
```

**规则**：
- 使用树形结构表示层级关系
- 叶子节点的 `children` 为空数组
- 支持任意深度
- 支持不同分支深度不同

**示例**：参见 `datasets/hierarchy_config.json`

### 标签信息文件 (dataset_labels_info.json)

用于固定层级分类，定义每层的标签列表。

**格式**：

```json
{
  "level1": {
    "labels": ["投资理财", "信贷服务", ...],
    "count": 6
  },
  "level2": {
    "labels": ["基金投资", "股票投资", ...],
    "count": 25
  },
  "level3": {
    "labels": ["开放式基金", "指数基金", ...],
    "count": 108
  }
}
```

---

## 数据集验证

### 使用验证脚本

项目提供了 `validate_dataset.py` 脚本用于验证数据集格式。

**验证所有数据集**：
```bash
python3 lib/python/validate_dataset.py --registry datasets/dataset_registry.json
```

**验证单个数据集**：
```bash
python3 lib/python/validate_dataset.py \
  --dataset financial_intent_fixed \
  --registry datasets/dataset_registry.json
```

### 验证检查项

1. **文件存在性**
   - 训练数据文件存在
   - 验证数据文件存在
   - 配置文件存在（如果需要）

2. **列完整性**
   - 包含所有必需列
   - 列名与配置匹配

3. **数据有效性**
   - 无空文本
   - 标签列无空值（允许的位置）
   - 标签值在有效范围内

4. **层级一致性**
   - 父级为空时子级也为空
   - 层级关系完整

5. **配置文件格式**
   - JSON格式正确
   - 包含必需字段

---

## 使用示例

### 添加新数据集

#### 步骤1：准备数据文件

创建 `datasets/my_dataset/train.csv` 和 `datasets/my_dataset/dev.csv`

#### 步骤2：在注册表中添加配置

编辑 `datasets/dataset_registry.json`：

```json
{
  "datasets": {
    "my_dataset": {
      "name": "我的数据集",
      "task_type": "single_label",
      "label_type": "single_label",
      "num_levels": 1,
      "data_paths": {
        "train": "datasets/my_dataset/train.csv",
        "validation": "datasets/my_dataset/dev.csv"
      },
      "config_path": null,
      "label_columns": ["label"],
      "text_column": "text",
      "num_labels": 5,
      "label_names": ["类别A", "类别B", "类别C", "类别D", "类别E"],
      "training_script": "train_single_label.py",
      "model_class": "BertForSingleLabelClassification",
      "description": "我的自定义数据集",
      "languages": ["zh"],
      "created_at": "2024-01-15"
    }
  }
}
```

#### 步骤3：验证数据集

```bash
python3 lib/python/validate_dataset.py --dataset my_dataset
```

#### 步骤4：使用通用训练脚本训练

```bash
python3 lib/python/train_universal.py \
  --dataset my_dataset \
  --batch_size 16 \
  --num_epochs 5
```

#### 步骤5：在Argo Workflow中使用

提交工作流时指定数据集名称：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: bert-training-
spec:
  entrypoint: universal-training-pipeline
  arguments:
    parameters:
      - name: dataset_name
        value: "my_dataset"  # 使用新添加的数据集
```

---

## 最佳实践

### 1. 数据集命名

- 使用小写字母和下划线
- 名称应描述数据集内容
- 格式：`{domain}_{task}_{variant}`

示例：
- `financial_intent_fixed`
- `jd_sentiment`
- `news_topic_multi`

### 2. 数据分割

- 训练集：70-80%
- 验证集：10-15%
- 测试集：10-15%（可选）

### 3. 标签编码

- 单标签：使用整数编码（0, 1, 2, ...）
- 多标签：使用列表或JSON数组
- 层级标签：使用字符串标签

### 4. 文本预处理

- 去除HTML标签
- 统一换行符
- 去除多余空格
- 保留中文和标点

### 5. 配置管理

- 所有配置在注册表中集中管理
- 避免硬编码路径
- 使用相对路径

---

## 常见问题

### Q1: 如何处理不平衡数据集？

A: 在训练时使用类别权重或过采样/欠采样技术。

### Q2: 动态层级和固定层级如何选择？

A:
- 如果层级数量固定且所有样本深度相同 → 固定层级
- 如果层级数量可变或样本深度不同 → 动态层级

### Q3: 如何添加新的标签类型？

A:
1. 确定任务类型（single/multi/hierarchical）
2. 准备符合格式的数据
3. 在注册表中添加配置
4. 验证数据集

### Q4: 数据集路径错误怎么办？

A: 检查以下几点：
1. 文件是否存在于指定路径
2. PVC是否正确挂载
3. 路径是否区分大小写

---

## 相关文档

- [训练指南](TRAINING.md)
- [推理服务文档](INFERENCE.md)
- [Argo Workflow使用指南](WORKFLOW.md)

---

**最后更新**: 2026-01-21
**维护者**: Claude Code
