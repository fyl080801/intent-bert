# Venv 环境配置报告

## ✅ 已完成的工作

### 1. 创建虚拟环境
- ✅ 使用 Python 3.12.11 创建了 venv 环境
- ✅ 路径: `/Users/fengyuanliang2/Source/test/bert-aliyun-test/venv`

### 2. 安装依赖包
所有关键依赖已成功安装并测试通过：
- ✅ NumPy 1.26.4 (已降级以兼容 PyTorch)
- ✅ PyTorch 2.2.2
- ✅ Transformers 4.57.5
- ✅ Pandas 2.3.3
- ✅ Scikit-learn 1.8.0
- ✅ Flask 3.1.2
- ✅ Flask-CORS 6.0.2
- ✅ Gunicorn 23.0.0
- ✅ python-dotenv 1.2.1

### 3. 修复 package.json
**问题**: npm scripts 使用系统 `python` 命令，可能不会使用 venv 环境

**修复**: 更新所有 Python 相关的 npm scripts，使用 `./venv/bin/python`

```diff
- "train:model": "python lib/python/train.py ..."
+ "train:model": "./venv/bin/python lib/python/train.py ..."

- "predict": "python lib/python/predict.py ..."
+ "predict": "./venv/bin/python lib/python/predict.py ..."

- "serve:model": "python lib/python/model_server.py"
+ "serve:model": "./venv/bin/python lib/python/model_server.py"

- "test:model": "python lib/python/predict.py ..."
+ "test:model": "./venv/bin/python lib/python/predict.py ..."
```

### 4. 验证模型自动下载
✅ 模型下载逻辑正确，以下代码会自动从 Hugging Face 下载模型：

- **train.py:230** - `BertTokenizer.from_pretrained('bert-base-chinese')`
- **models.py:182** - `BertForMultiLabelClassification.from_pretrained('bert-base-chinese')`

首次运行时，模型会自动下载到 `~/.cache/huggingface/` 目录。

### 5. NumPy 兼容性修复
**问题**: PyTorch 2.2.2 与 NumPy 2.x 不兼容

**修复**: 降级到 NumPy 1.26.4

```bash
pip uninstall numpy -y && pip install "numpy==1.26.4"
```

## 📋 训练脚本验证

### train.py 功能检查
✅ 数据加载和预处理
✅ 标签编码 (一级、二级、三级)
✅ 多任务模型架构
✅ 自定义 Trainer (加权损失: 0.3 + 0.3 + 0.4)
✅ 评估指标 (accuracy, F1, precision, recall)
✅ 模型和配置保存

### models.py 功能检查
✅ `BertForMultiLabelClassification` - 多标签分类模型
✅ `BertForHierarchicalClassification` - 层级分类模型
✅ `create_multitask_model()` - 模型创建辅助函数

## 🚀 使用方法

### 方式 1: 使用 NPM 命令 (推荐)
```bash
# 训练模型
npm run train:model

# 交互式预测
npm run predict

# 启动模型服务
npm run serve:model

# 测试模型
npm run test:model
```

### 方式 2: 直接使用 Python
```bash
# 激活 venv
source venv/bin/activate

# 训练模型
python lib/python/train.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --output_dir models

# 交互式预测
python lib/python/predict.py --model_path models --interactive

# 启动模型服务
python lib/python/model_server.py
```

### 自定义训练参数
```bash
source venv/bin/activate

python lib/python/train.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --model_name bert-base-chinese \
  --output_dir models \
  --max_length 128 \
  --batch_size 16 \
  --num_epochs 5 \
  --learning_rate 2e-5 \
  --warmup_steps 500 \
  --weight_decay 0.01
```

## 📦 模型文件结构

训练完成后，`models/` 目录将包含：
```
models/
├── label_encoders.json       # 标签编码器映射
├── training_config.json      # 训练配置
├── eval_results.json         # 评估结果
├── config.json               # 模型配置
├── pytorch_model.bin         # PyTorch 模型权重
├── tokenizer_config.json     # Tokenizer 配置
├── vocab.txt                 # 词汇表
└── special_tokens_map.json   # 特殊 token 映射
```

## ⚠️ 注意事项

1. **首次运行**: 首次训练时会自动下载 BERT 模型 (~400MB)，需要稳定的网络连接
2. **CUDA 支持**: 如果有 NVIDIA GPU，PyTorch 会自动使用 CUDA 加速训练
3. **数据集**: 确保数据集文件存在于 `datasets/` 目录
4. **磁盘空间**: 训练过程中会保存多个 checkpoint，确保有足够磁盘空间

## ✅ 测试脚本

已创建 `test_venv_setup.sh` 用于快速验证环境配置：

```bash
./test_venv_setup.sh
```

测试内容：
- Python 版本
- 依赖包版本
- BERT 组件导入
- 模型自动下载
- 数据集文件检查
- 输出目录检查

## 🎯 下一步

环境已完全配置好，可以开始训练模型：

```bash
npm run train:model
```

训练时间取决于：
- 数据集大小
- 训练轮数 (默认 5 epochs)
- 是否使用 GPU
- 硬件性能
