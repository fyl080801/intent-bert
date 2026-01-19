#!/bin/bash
# 测试 venv 环境配置和模型下载

echo "======================================"
echo "测试 venv 环境配置"
echo "======================================"
echo ""

# 激活 venv
source venv/bin/activate

echo "1. 检查 Python 版本"
python --version
echo ""

echo "2. 检查关键依赖包"
python -c "
import numpy
import torch
import transformers
import pandas
import sklearn
import flask

print(f'   ✅ NumPy: {numpy.__version__}')
print(f'   ✅ PyTorch: {torch.__version__}')
print(f'   ✅ Transformers: {transformers.__version__}')
print(f'   ✅ Pandas: {pandas.__version__}')
print(f'   ✅ Scikit-learn: {sklearn.__version__}')
print(f'   ✅ Flask: {flask.__version__}')
"
echo ""

echo "3. 测试 BERT 模型组件"
python -c "
from transformers import BertTokenizer, BertConfig, BertModel
from lib.python.models import BertForMultiLabelClassification

print('   ✅ BERT Tokenizer 导入成功')
print('   ✅ BERT Config 导入成功')
print('   ✅ BERT Model 导入成功')
print('   ✅ 自定义多标签分类模型导入成功')
"
echo ""

echo "4. 测试模型自动下载（首次运行会下载模型）"
python -c "
from transformers import BertTokenizer

# 测试 tokenizer 下载
tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
print('   ✅ BERT Tokenizer 下载/加载成功')
print(f'   ✅ 词汇表大小: {len(tokenizer)}')
"
echo ""

echo "5. 检查数据集文件"
if [ -f "datasets/financial_intent_dataset.csv" ]; then
    echo "   ✅ 训练数据集存在"
else
    echo "   ⚠️  训练数据集不存在: datasets/financial_intent_dataset.csv"
fi

if [ -f "datasets/financial_intent_validation.csv" ]; then
    echo "   ✅ 验证数据集存在"
else
    echo "   ⚠️  验证数据集不存在: datasets/financial_intent_validation.csv"
fi
echo ""

echo "6. 检查输出目录"
mkdir -p models
echo "   ✅ 模型输出目录已创建: models/"
echo ""

echo "======================================"
echo "✅ 环境配置测试完成！"
echo "======================================"
echo ""
echo "可以运行以下命令开始训练："
echo "  npm run train:model"
echo ""
echo "或者直接使用 Python："
echo "  source venv/bin/activate"
echo "  python lib/python/train.py --train_data datasets/financial_intent_dataset.csv --val_data datasets/financial_intent_validation.csv --output_dir models"
