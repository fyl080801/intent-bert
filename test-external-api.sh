#!/bin/bash

# BERT 推理服务外部访问测试脚本
# 通过公网 IP 和域名访问

SERVICE_URL="http://89.208.241.158:8080"

echo "=========================================="
echo "BERT 推理服务外部访问测试"
echo "服务地址: $SERVICE_URL"
echo "域名: bert.fyl080801.uk"
echo "=========================================="

# 1. 健康检查
echo -e "\n📡 1. 健康检查:"
curl -s ${SERVICE_URL}/health \
  -H "Host: bert.fyl080801.uk" \
  --max-time 10 \
  | python3 -m json.tool 2>/dev/null || \
curl -s ${SERVICE_URL}/health \
  -H "Host: bert.fyl080801.uk" \
  --max-time 10

# 2. 单条预测
echo -e "\n\n🔍 2. 单条文本预测:"
echo "输入: 我想查询银行卡余额"
curl -s -X POST ${SERVICE_URL}/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"text": "我想查询银行卡余额"}' \
  --max-time 30 \
  | python3 -m json.tool 2>/dev/null || \
curl -s -X POST ${SERVICE_URL}/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"text": "我想查询银行卡余额"}' \
  --max-time 30

# 3. 批量预测
echo -e "\n\n📊 3. 批量文本预测:"
echo "输入: 基金投资、个人贷款、转账汇款"
curl -s -X POST ${SERVICE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{
    "texts": [
      "我想买一些基金投资",
      "我要申请个人贷款",
      "怎么转账到其他银行"
    ]
  }' \
  --max-time 60 \
  | python3 -m json.tool 2>/dev/null || \
curl -s -X POST ${SERVICE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"texts": ["我想买一些基金投资", "我要申请个人贷款", "怎么转账到其他银行"]}' \
  --max-time 60

# 4. 模型信息
echo -e "\n\n💾 4. 模型信息:"
curl -s ${SERVICE_URL}/model_info \
  -H "Host: bert.fyl080801.uk" \
  --max-time 10 \
  | python3 -m json.tool 2>/dev/null || \
curl -s ${SERVICE_URL}/model_info \
  -H "Host: bert.fyl080801.uk" \
  --max-time 10

echo -e "\n\n=========================================="
echo "✅ 测试完成"
echo ""
echo "💡 提示:"
echo "  - 公网 IP 访问必须添加 Host 头"
echo "  - 配置 DNS 后可直接使用域名访问"
echo "  - DNS 配置: bert.fyl080801.uk A 89.208.241.158"
echo "=========================================="
