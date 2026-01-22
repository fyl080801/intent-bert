#!/bin/bash

# BERT 推理服务快速测试脚本

BASE_URL="http://192.168.68.110:30500"

echo "=========================================="
echo "BERT 推理服务 API 测试"
echo "服务地址: $BASE_URL"
echo "=========================================="

# 1. 健康检查
echo -e "\n📡 1. 健康检查:"
curl -s ${BASE_URL}/health | python3 -m json.tool 2>/dev/null || curl -s ${BASE_URL}/health

# 2. 单条预测
echo -e "\n\n🔍 2. 单条文本预测:"
echo "输入: 我想查询银行卡余额"
curl -s -X POST ${BASE_URL}/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}' | python3 -m json.tool 2>/dev/null || \
curl -s -X POST ${BASE_URL}/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}'

# 3. 批量预测
echo -e "\n\n📊 3. 批量文本预测:"
echo "输入: 信用卡额度怎么提升、我要申请个人贷款、转账给朋友"
curl -s -X POST ${BASE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["信用卡额度怎么提升", "我要申请个人贷款", "转账给朋友"]}' | python3 -m json.tool 2>/dev/null || \
curl -s -X POST ${BASE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["信用卡额度怎么提升", "我要申请个人贷款", "转账给朋友"]}'

# 4. 模型信息
echo -e "\n\n💾 4. 模型信息:"
curl -s ${BASE_URL}/model_info | python3 -m json.tool 2>/dev/null || curl -s ${BASE_URL}/model_info

echo -e "\n\n=========================================="
echo "✅ 测试完成"
echo "=========================================="
