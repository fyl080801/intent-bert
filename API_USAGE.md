# BERT 推理服务 API 使用说明

## 服务访问方式

### 方式一：通过域名访问（需要 DNS 配置）

域名：`bert.fyl080801.uk`

**DNS 配置**：
需要将 `bert.fyl080801.uk` 解析到任意 K8s 节点 IP：
- 192.168.68.110 (fyl-workstation)
- 或其他集群节点 IP

### 方式二：通过 Ingress NodePort 访问

```
http://<NODE_IP>:8080
```

- **fyl-workstation**: http://192.168.68.110:8080
- **其他节点**: http://<节点IP>:8080

**重要**：请求时需要添加 Host 头：`Host: bert.fyl080801.uk`

### 方式三：通过 NodePort 直接访问

```
http://192.168.68.110:30500
```

---

## API 接口

### 1. 健康检查

```bash
curl -X GET http://192.168.68.110:30500/health
```

**响应示例**：
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

---

### 2. 单条文本预测

**接口**：`POST /predict`

**请求示例**：
```bash
curl -X POST http://192.168.68.110:30500/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "我想查询银行卡余额"
  }'
```

**通过 Ingress 访问**：
```bash
curl -X POST http://192.168.68.110:8080/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{
    "text": "我想查询银行卡余额"
  }'
```

**通过域名访问**（需配置 DNS）：
```bash
curl -X POST http://bert.fyl080801.uk/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "我想查询银行卡余额"
  }'
```

**响应示例**：
```json
{
  "label_level1": "信贷服务",
  "label_level2": "信用卡服务",
  "label_level3": "额度提升",
  "confidence_level1": 0.6582,
  "confidence_level2": 0.4635,
  "confidence_level3": 0.0737,
  "overall_confidence": 0.3985
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `label_level1` | string | 一级分类标签（6类） |
| `label_level2` | string | 二级分类标签（24类） |
| `label_level3` | string | 三级分类标签（108类） |
| `confidence_level1` | float | 一级标签置信度（0-1） |
| `confidence_level2` | float | 二级标签置信度（0-1） |
| `confidence_level3` | float | 三级标签置信度（0-1） |
| `overall_confidence` | float | 综合置信度（平均值） |

---

### 3. 批量文本预测

**接口**：`POST /predict_batch`

**请求示例**：
```bash
curl -X POST http://192.168.68.110:30500/predict_batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "基金怎么买",
      "我要申请贷款",
      "怎么转账给朋友"
    ]
  }'
```

**响应示例**：
```json
{
  "results": [
    {
      "text": "基金怎么买",
      "label_level1": "投资理财",
      "label_level2": "基金投资",
      "label_level3": "开放式基金",
      "confidence_level1": 0.9234,
      "confidence_level2": 0.8123,
      "confidence_level3": 0.7234,
      "overall_confidence": 0.8197
    },
    {
      "text": "我要申请贷款",
      "label_level1": "信贷服务",
      "label_level2": "个人贷款",
      "label_level3": "消费贷",
      "confidence_level1": 0.9123,
      "confidence_level2": 0.8456,
      "confidence_level3": 0.7234,
      "overall_confidence": 0.8271
    },
    {
      "text": "怎么转账给朋友",
      "label_level1": "交易服务",
      "label_level2": "转账汇款",
      "label_level3": "跨行转账",
      "confidence_level1": 0.9456,
      "confidence_level2": 0.8789,
      "confidence_level3": 0.6789,
      "overall_confidence": 0.8345
    }
  ]
}
```

---

### 4. 模型信息

**接口**：`GET /model_info`

**请求示例**：
```bash
curl -X GET http://192.168.68.110:30500/model_info
```

**响应示例**：
```json
{
  "model_path": "/app/models/financial_intent_fixed-600e8423-73dd-47e4-9a50-067ecd484a0a",
  "device": "cuda",
  "max_length": 128,
  "num_labels": {
    "level1": 6,
    "level2": 24,
    "level3": 108
  },
  "labels": {
    "level1": ["交易服务", "产品咨询", "信贷服务", "投资理财", "账户服务", "风险合规"],
    "level2": ["个人贷款", "交易查询", "产品对比", "产品推荐", ...],
    "level3": ["A股交易", "个人开户", "临时额度", ...]
  }
}
```

---

## 完整测试脚本

```bash
#!/bin/bash

# 设置服务地址
BASE_URL="http://192.168.68.110:30500"
# 或者使用域名（需配置 DNS）
# BASE_URL="http://bert.fyl080801.uk"

echo "=========================================="
echo "BERT 推理服务 API 测试"
echo "=========================================="

# 1. 健康检查
echo -e "\n1. 健康检查:"
curl -s ${BASE_URL}/health | json_pp || curl -s ${BASE_URL}/health

# 2. 单条预测
echo -e "\n\n2. 单条文本预测:"
curl -s -X POST ${BASE_URL}/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}' | json_pp || \
curl -s -X POST ${BASE_URL}/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}'

# 3. 批量预测
echo -e "\n\n3. 批量文本预测:"
curl -s -X POST ${BASE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "信用卡额度怎么提升",
      "我要申请个人贷款",
      "转账给朋友"
    ]
  }' | json_pp || \
curl -s -X POST ${BASE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["信用卡额度怎么提升", "我要申请个人贷款", "转账给朋友"]}'

# 4. 模型信息
echo -e "\n\n4. 模型信息:"
curl -s ${BASE_URL}/model_info | json_pp || curl -s ${BASE_URL}/model_info

echo -e "\n\n=========================================="
echo "测试完成"
echo "=========================================="
```

---

## Python 客户端示例

```python
import requests
import json

class BERTInferenceClient:
    def __init__(self, base_url="http://192.168.68.110:30500"):
        self.base_url = base_url

    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def predict(self, text: str):
        """单条预测"""
        response = requests.post(
            f"{self.base_url}/predict",
            json={"text": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def predict_batch(self, texts: list):
        """批量预测"""
        response = requests.post(
            f"{self.base_url}/predict_batch",
            json={"texts": texts},
            timeout=60
        )
        response.raise_for_status()
        return response.json()

    def model_info(self):
        """获取模型信息"""
        response = requests.get(f"{self.base_url}/model_info")
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = BERTInferenceClient()

    # 健康检查
    print("健康检查:", client.health_check())

    # 单条预测
    result = client.predict("我想买一些基金")
    print(f"预测结果: {result}")

    # 批量预测
    results = client.predict_batch([
        "基金怎么买",
        "我要申请贷款"
    ])
    print(f"批量结果: {json.dumps(results, ensure_ascii=False, indent=2)}")
```

---

## 错误处理

**400 错误**：请求参数错误
```json
{
  "error": "Missing \"text\" field in request"
}
```

**500 错误**：服务器内部错误
```json
{
  "error": "预测失败: 具体错误信息"
}
```

---

## 性能说明

- **设备**: NVIDIA GeForce RTX 4070 Ti SUPER
- **单条预测**: ~50-100ms
- **批量预测**: 可同时处理多个请求
- **最大文本长度**: 512 字符
- **推荐批量大小**: 8-16 条

---

## 标签分类说明

### 一级标签（6类）
- 投资理财
- 信贷服务
- 账户服务
- 交易服务
- 产品咨询
- 风险合规

### 二级标签（24类）
包括：基金投资、个人贷款、信用卡服务、转账汇款、理财产品等

### 三级标签（108类）
包括：开放式基金、房贷、临时额度、跨行转账等细粒度分类
