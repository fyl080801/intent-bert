# BERT 模型训练报告

**日期**: 2025-01-15
**模型**: bert-base-chinese 多任务分类
**状态**: ❌ 训练失败（在评估阶段）

---

## 📊 训练配置

### 数据集
- **训练集**: 2000 样本
- **验证集**: 300 样本
- **一级标签**: 6 个
- **二级标签**: 24 个
- **三级标签**: 108 个

### 模型架构
- **基础模型**: bert-base-chinese
- **任务类型**: 多任务学习（三级层级分类）
- **损失权重**:
  - Level 1 (一级): 0.3
  - Level 2 (二级): 0.3
  - Level 3 (三级): 0.4

### 超参数
- **最大序列长度**: 128
- **批次大小**: 16
- **训练轮数**: 5 epochs
- **学习率**: 2e-5
- **预热步数**: 500
- **权重衰减**: 0.01
- **评估策略**: 每 500 步
- **保存策略**: 每 500 步

---

## 🚀 训练进度

### 时间线
| 里程碑 | 步数 | 时间 | 状态 |
|--------|------|------|------|
| 开始训练 | 0/625 | 0:00 | ✅ |
| 100 步 | 100/625 (16%) | ~6 分钟 | ✅ |
| 200 步 | 200/625 (32%) | ~12 分钟 | ✅ |
| 300 步 | 300/625 (48%) | ~21 分钟 | ✅ |
| 400 步 | 400/625 (64%) | ~29 分钟 | ✅ |
| 500 步 | 500/625 (80%) | ~36 分钟 | ❌ 失败 |

### 训练速度
- **平均速度**: ~4.3 秒/步
- **总耗时**: ~36 分钟（500 步）
- **预计完成时间**: ~45 分钟（完整 625 步）

---

## 📈 训练损失

**观察到的损失下降**（每 100 步）：

| Step | Loss | Gradient Norm | Learning Rate | Epoch |
|-------|------|---------------|---------------|-------|
| 100 | 3.4535 | 9.23 | 3.96e-06 | 0.8 |
| 200 | 3.0918 | 6.28 | 7.96e-06 | 1.6 |
| 300 | 2.4587 | 6.87 | 1.196e-05 | 2.4 |
| 400 | 1.8682 | 5.65 | 1.596e-05 | 3.2 |
| 500 | 1.4093 | 4.45 | 1.996e-05 | 4.0 |

**损失趋势**: ✅ 稳定下降
- 从 3.45 → 1.41（下降 59%）
- 梯度范数从 9.23 → 4.45（收敛良好）
- 学习率按计划逐步增加

---

## ❌ 错误详情

### 发生位置
- **阶段**: 评估（Evaluation）
- **时间**: 第 500 步（80%）
- **触发点**: 执行评估指标计算时

### 错误类型
```
TypeError: Unsupported types (<class 'NoneType'>) passed to `_pad_across_processes`.
Only nested list/tuple/dicts of objects that are valid for `is_torch_tensor` should be passed.
```

### 根本原因
在评估阶段，`compute_metrics` 函数返回的数据格式存在问题，导致 transformers 无法正确处理数据填充（padding）。

---

## 🔍 问题分析

### 根本原因
`compute_metrics` 函数返回的 predictions 或 labels 包含 `None` 值，在尝试进行批次填充时导致类型错误。

### 可能原因
1. **预测输出格式**: 模型输出的 logits 格式与预期不符
2. **标签数据格式**: 标签编码或传递过程中存在 None 值
3. **评估指标计算**: 指标计算逻辑返回了包含 None 的数据结构

### 影响范围
- ❌ 模型未完成完整训练（还剩 125 步）
- ❌ 无法保存最终模型
- ❌ 未生成评估结果报告
- ❌ 未保存最终 checkpoint

---

## 📁 生成的文件

### ✅ 已生成
- `models/label_encoders.json` (6.7KB) - 标签编码器映射

### ❌ 未生成
- `models/pytorch_model.bin` - 模型权重
- `models/config.json` - 模型配置
- `models/eval_results.json` - 评估结果
- `models/training_config.json` - 训练配置
- `models/tokenizer_config.json` - Tokenizer 配置
- `models/vocab.txt` - 词汇表

---

## 💡 建议修复方案

### 1. 修复 compute_metrics 函数
确保函数返回的所有值都是有效的 tensor，不包含 None：

```python
def compute_metrics(pred) -> Dict[str, float]:
    # 处理模型输出
    if isinstance(pred.predictions, dict):
        logits1 = pred.predictions['logits_level1']
        logits2 = pred.predictions['logits_level2']
        logits3 = pred.predictions['logits_level3']
    else:
        logits1, logits2, logits3 = pred.predictions

    labels1 = pred.label_ids['level1']
    labels2 = pred.label_ids['level2']
    labels3 = pred.label_ids['level3']

    # 确保没有 None 值
    if logits1 is None or logits2 is None or logits3 is None:
        return {'error': 'Model output is None'}

    if labels1 is None or labels2 is None or labels3 is None:
        return {'error': 'Labels are None'}

    # 继续计算指标...
```

### 2. 添加错误处理
在评估阶段添加 try-except 块：

```python
def compute_metrics(pred) -> Dict[str, float]:
    try:
        # 原有的计算逻辑
        ...
    except Exception as e:
        print(f"Error in compute_metrics: {e}")
        return {'error': str(e)}
```

### 3. 禁用评估模式
临时解决方案 - 仅训练不评估：

```python
training_args = TrainingArguments(
    ...
    evaluation_strategy="no",  # 禁用评估
    save_strategy="no",        # 禁用保存
    ...
)
```

### 4. 使用自定义评估循环
不使用 Trainer 的内置评估，而是在训练后手动评估：

```python
# 训练完成后手动评估
trainer.train()
eval_results = trainer.evaluate()
# 或者自定义评估逻辑
```

---

## 📊 训练成果评估

尽管训练未能完成，但从已完成的 80% 训练来看：

### ✅ 积极方面
1. **损失稳定下降**: 从 3.45 降至 1.41
2. **梯度收敛**: 梯度范数从 9.23 → 4.45
3. **训练稳定**: 没有出现 NaN 或爆炸
4. **模型学习**: 损失持续下降表明模型在学习

### ⚠️ 需要关注
1. **评估阶段失败**: 需要修复评估逻辑
2. **模型未保存**: 需要确保checkpoint保存正常
3. **无法验证性能**: 缺少准确率、F1 等指标

---

## 🎯 下一步行动

### 立即行动
1. **修复 compute_metrics 函数** - 添加 None 值检查
2. **添加错误日志** - 详细记录评估过程中的数据格式
3. **简化评估逻辑** - 逐步验证每个部分

### 后续改进
1. **增加日志输出** - 记录中间结果
2. **数据验证** - 在训练前验证数据格式
3. **单元测试** - 测试评估函数

---

## 📝 已修复的问题回顾

在本次训练过程中，我们已修复了以下问题：

1. ✅ **NumPy 版本兼容性** - 降级到 1.26.4
2. ✅ **JSON 序列化** - 修复 numpy int64 → Python int
3. ✅ **Transformers API** - `evaluation_strategy` → `eval_strategy`
4. ✅ **缺少 accelerate** - 安装 accelerate 1.12.0
5. ✅ **数据格式** - 添加自定义 `custom_data_collator`
6. ✅ **方法签名** - 更新 `compute_loss` 添加 `num_items_in_batch`

### 🔴 当前待修复
- ❌ **评估阶段 None 值问题** - `compute_metrics` 函数返回 None

---

## 📚 技术栈总结

- **Python**: 3.12.11 (venv)
- **PyTorch**: 2.2.2
- **Transformers**: 4.57.5
- **Accelerate**: 1.12.0
- **NumPy**: 1.26.4
- **设备**: CPU (MacOS)

---

**报告生成时间**: 2025-01-15
**训练持续时间**: ~36 分钟（500/625 步）
**状态**: 需要修复评估逻辑后重新训练
