# 灵活多级BERT分类系统使用指南

## 概述

本系统实现了灵活的多级标签BERT分类，支持：
- ✅ **动态配置层级结构** - 通过JSON配置文件定义标签层级
- ✅ **不规则层级树** - 不同分支可以有不同深度
- ✅ **可扩展架构** - 无需修改代码即可增加层级数量

## 架构设计

### 核心组件

1. **hierarchy_config.py** - 层级配置解析器
   - 从树形JSON配置提取层级信息
   - 自动计算层级深度和标签数量
   - 生成模型初始化所需的配置

2. **dynamic_models.py** - 动态层级BERT模型
   - `BertForDynamicHierarchicalClassification` - 主模型类
   - 根据配置动态创建N个分类头
   - 支持层级感知的特征传递

3. **train_dynamic.py** - 动态层级训练脚本
   - 支持可变层级深度的数据集
   - 自动处理mask和loss计算
   - 完整的评估指标

4. **predict_dynamic.py** - 动态层级预测脚本
   - 单条/批量/文件预测
   - 交互式预测模式
   - 完整的路径和置信度输出

## 配置文件格式

### hierarchy_config.json 示例

```json
{
  "version": "1.0",
  "labels": [
    {
      "name": "投资理财",
      "children": [
        {
          "name": "基金投资",
          "children": [
            {"name": "开放式基金", "children": []},
            {"name": "指数基金", "children": []}
          ]
        },
        {
          "name": "股票投资",
          "children": [
            {
              "name": "A股交易",
              "children": [
                {"name": "普通交易", "children": []},
                {"name": "融资融券", "children": []}
              ]
            }
          ]
        }
      ]
    },
    {
      "name": "账户服务",
      "children": [
        {"name": "开户注销", "children": []}
      ]
    }
  ]
}
```

### 关键特性

- **树形结构** - 直观的父子关系
- **自动计算深度** - 无需手动标记层级
- **支持不规则** - "基金投资"只有3级，"A股交易"有4级

## 使用方法

### 1. 准备配置文件

创建或修改 `datasets/hierarchy_config.json`：

```bash
# 验证配置文件
python -c "
from lib.python.hierarchy_config import HierarchyConfigParser
parser = HierarchyConfigParser('datasets/hierarchy_config.json')
parser.print_summary()
"
```

### 2. 训练模型

```bash
# 基础训练
./venv/bin/python lib/python/train_dynamic.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --hierarchy_config datasets/hierarchy_config.json \
  --output_dir models_dynamic \
  --batch_size 16 \
  --num_epochs 5

# 高级选项
./venv/bin/python lib/python/train_dynamic.py \
  --model_name bert-base-chinese \
  --learning_rate 2e-5 \
  --warmup_steps 500 \
  --model_version v1
```

### 3. 预测

#### 交互式模式

```bash
./venv/bin/python lib/python/predict_dynamic.py \
  --model_path models_dynamic \
  --mode interactive
```

#### 单条预测

```bash
./venv/bin/python lib/python/predict_dynamic.py \
  --model_path models_dynamic \
  --mode single \
  --text "我想买开放式基金"
```

#### 文件预测

```bash
./venv/bin/python lib/python/predict_dynamic.py \
  --model_path models_dynamic \
  --mode file \
  --input_file test_data.csv \
  --output_file predictions.csv \
  --text_column text
```

## 输出格式

### 预测结果示例

```json
{
  "text": "我想买开放式基金",
  "predictions": [
    {
      "level": 0,
      "name": "投资理财",
      "label": "投资理财",
      "confidence": 0.95
    },
    {
      "level": 1,
      "name": "基金投资",
      "label": "基金投资",
      "confidence": 0.88
    },
    {
      "level": 2,
      "name": "开放式基金",
      "label": "开放式基金",
      "confidence": 0.92
    }
  ],
  "full_path": "投资理财 > 基金投资 > 开放式基金",
  "confidence_avg": 0.917,
  "num_levels": 3
}
```

## 扩展层级

### 添加新层级

只需修改配置文件，无需改动代码：

```json
{
  "name": "股票投资",
  "children": [
    {
      "name": "A股交易",
      "children": [
        {
          "name": "普通交易",
          "children": [
            {"name": "限价委托", "children": []},
            {"name": "市价委托", "children": []}
          ]
        }
      ]
    }
  ]
}
```

重新训练即可：

```bash
./venv/bin/python lib/python/train_dynamic.py \
  --hierarchy_config datasets/hierarchy_config.json
```

## 数据格式要求

### 训练数据 CSV

```csv
text,label_level1,label_level2,label_level3
我想买开放式基金,投资理财,基金投资,开放式基金
如何开户,账户服务,开户注销,个人开户
```

### 可变深度支持

不同样本可以有不同深度：

```csv
text,label_level1,label_level2,label_level3,label_level4
基金投资,投资理财,基金投资,开放式基金,
股票交易,投资理财,股票投资,A股交易,普通交易
简单咨询,账户服务,开户注销,,
```

## 与原系统对比

| 特性 | 原系统 (3级固定) | 新系统 (动态层级) |
|------|-----------------|------------------|
| 层级数量 | 固定3级 | 动态配置 |
| 层级结构 | 规则（所有分支同深） | 支持不规则 |
| 扩展性 | 需修改代码 | 仅修改配置 |
| 数据深度 | 必须完整3级 | 支持可变深度 |
| 模型架构 | 硬编码3个分类头 | 动态N个分类头 |

## API接口（未来扩展）

计划添加的REST API端点：

```
POST /api/predict
  单条文本预测

POST /api/predict-batch
  批量文本预测

GET /api/model-info
  返回层级结构信息

POST /api/predict-level
  指定预测到第几层
```

## 故障排查

### 常见问题

**Q: 提示找不到配置文件**
```
A: 确保 hierarchy_config.json 路径正确，使用绝对路径或相对于项目根目录的路径
```

**Q: 训练时loss为NaN**
```
A: 检查学习率，尝试降低到 1e-5 或 5e-6
```

**Q: 预测结果层级不对**
```
A: 确认模型加载的标签映射与训练时一致
```

**Q: 内存不足**
```
A: 减小 batch_size 或使用梯度累积
```

## 性能优化建议

1. **数据预处理** - 提前构建标签编码映射
2. **批处理** - 预测时使用合理的batch_size
3. **混合精度** - 训练时使用FP16（需要GPU支持）
4. **模型选择** - 根据数据量选择合适的BERT模型

## 下一步计划

- [ ] 添加层级约束推理（父子关系验证）
- [ ] 支持增量学习（添加新标签不需全量重训）
- [ ] REST API服务封装
- [ ] Web UI可视化界面
- [ ] 模型蒸馏和加速

## 相关文件

```
lib/python/
├── hierarchy_config.py        # 配置解析器
├── dynamic_models.py           # 动态模型定义
├── train_dynamic.py            # 训练脚本
└── predict_dynamic.py          # 预测脚本

datasets/
└── hierarchy_config.json       # 层级配置文件

models_dynamic/                 # 训练输出目录
├── hierarchical_label_mapping.json
├── label_encoders.json
└── training_config.json
```

## 引用

如果使用本系统，请引用：

```
Flexible Multi-Level BERT Classification System
Version 1.0
https://github.com/your-repo/bert-aliyun-test
```
