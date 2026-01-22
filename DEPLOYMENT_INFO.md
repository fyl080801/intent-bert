# BERT 推理服务部署说明

## 集群信息

- **Ingress Controller**: ingress-nginx (NodePort)
- **外部节点**: bandwagon (89.208.241.158)
- **HTTP 端口**: 8080
- **HTTPS 端口**: 8443

## 服务访问方式

### 方式一：通过公网 IP + Ingress Port 访问

```bash
# 使用 bandwagon 节点的公网 IP
http://89.208.241.158:8080
```

**重要**：请求时必须添加 Host 头：`Host: bert.fyl080801.uk`

### 方式二：通过域名访问（推荐）

**域名**: `bert.fyl080801.uk`

**DNS 配置**：
```
bert.fyl080801.uk  A  89.208.241.158
```

配置 DNS 后可以直接访问：
```bash
http://bert.fyl080801.uk
```

---

## API 调用示例

### 1. 健康检查

```bash
# 通过公网 IP 访问（带 Host 头）
curl -X GET http://89.208.241.158:8080/health \
  -H "Host: bert.fyl080801.uk"

# 通过域名访问（需先配置 DNS）
curl -X GET http://bert.fyl080801.uk/health
```

### 2. 单条文本预测

```bash
# 通过公网 IP 访问
curl -X POST http://89.208.241.158:8080/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{
    "text": "我想查询银行卡余额"
  }'

# 通过域名访问
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

### 3. 批量文本预测

```bash
# 通过公网 IP 访问
curl -X POST http://89.208.241.158:8080/predict_batch \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{
    "texts": [
      "信用卡额度怎么提升",
      "我要申请个人贷款",
      "转账给朋友"
    ]
  }'

# 通过域名访问
curl -X POST http://bert.fyl080801.uk/predict_batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "信用卡额度怎么提升",
      "我要申请个人贷款",
      "转账给朋友"
    ]
  }'
```

### 4. 模型信息

```bash
# 通过公网 IP 访问
curl -X GET http://89.208.241.158:8080/model_info \
  -H "Host: bert.fyl080801.uk"

# 通过域名访问
curl -X GET http://bert.fyl080801.uk/model_info
```

---

## Python 客户端示例

```python
import requests
import json

class BERTInferenceClient:
    """BERT 推理服务客户端"""

    def __init__(self, base_url="http://bert.fyl080801.uk"):
        """
        初始化客户端
        :param base_url: 服务地址
                        - http://bert.fyl080801.uk (域名访问)
                        - http://89.208.241.158:8080 (公网 IP 访问，需添加 Host 头)
        """
        self.base_url = base_url
        self.session = requests.Session()

        # 如果使用 IP 访问，自动添加 Host 头
        if "89.208.241.158" in base_url:
            self.session.headers.update({"Host": "bert.fyl080801.uk"})

    def health_check(self):
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health", timeout=10)
        response.raise_for_status()
        return response.json()

    def predict(self, text: str):
        """
        单条文本预测
        :param text: 待预测文本
        :return: 预测结果
        """
        response = self.session.post(
            f"{self.base_url}/predict",
            json={"text": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def predict_batch(self, texts: list):
        """
        批量文本预测
        :param texts: 待预测文本列表
        :return: 预测结果列表
        """
        response = self.session.post(
            f"{self.base_url}/predict_batch",
            json={"texts": texts},
            timeout=60
        )
        response.raise_for_status()
        return response.json()

    def model_info(self):
        """获取模型信息"""
        response = self.session.get(f"{self.base_url}/model_info", timeout=10)
        response.raise_for_status()
        return response.json()


# 使用示例
if __name__ == "__main__":
    # 方式一：域名访问（推荐）
    client = BERTInferenceClient("http://bert.fyl080801.uk")

    # 方式二：公网 IP 访问
    # client = BERTInferenceClient("http://89.208.241.158:8080")

    # 健康检查
    print("健康检查:", client.health_check())

    # 单条预测
    result = client.predict("我想买一些基金进行投资")
    print(f"\n单条预测结果:")
    print(f"  文本: 我想买一些基金进行投资")
    print(f"  一级: {result['label_level1']} ({result['confidence_level1']:.2%})")
    print(f"  二级: {result['label_level2']} ({result['confidence_level2']:.2%})")
    print(f"  三级: {result['label_level3']} ({result['confidence_level3']:.2%})")
    print(f"  综合置信度: {result['overall_confidence']:.2%}")

    # 批量预测
    texts = [
        "信用卡额度怎么提升",
        "我要申请个人贷款买房",
        "怎么转账到其他银行"
    ]
    results = client.predict_batch(texts)

    print(f"\n批量预测结果:")
    for i, result in enumerate(results['results'], 1):
        print(f"\n{i}. 文本: {result['text']}")
        print(f"   一级: {result['label_level1']} ({result['confidence_level1']:.2%})")
        print(f"   二级: {result['label_level2']} ({result['confidence_level2']:.2%})")
        print(f"   三级: {result['label_level3']} ({result['confidence_level3']:.2%})")

    # 模型信息
    info = client.model_info()
    print(f"\n模型信息:")
    print(f"  设备: {info['device']}")
    print(f"  标签数量: L1={info['num_labels']['level1']}, "
          f"L2={info['num_labels']['level2']}, L3={info['num_labels']['level3']}")
```

---

## 测试脚本

保存为 `test-external-api.sh`：

```bash
#!/bin/bash

# 配置服务地址
SERVICE_URL="http://89.208.241.158:8080"
# 如果已配置 DNS，可以使用域名
# SERVICE_URL="http://bert.fyl080801.uk"

echo "=========================================="
echo "BERT 推理服务外部访问测试"
echo "服务地址: $SERVICE_URL"
echo "=========================================="

# 1. 健康检查
echo -e "\n📡 1. 健康检查:"
curl -s ${SERVICE_URL}/health \
  -H "Host: bert.fyl080801.uk" \
  | python3 -m json.tool 2>/dev/null || \
curl -s ${SERVICE_URL}/health -H "Host: bert.fyl080801.uk"

# 2. 单条预测
echo -e "\n\n🔍 2. 单条文本预测:"
echo "输入: 我想查询银行卡余额"
curl -s -X POST ${SERVICE_URL}/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"text": "我想查询银行卡余额"}' \
  | python3 -m json.tool 2>/dev/null || \
curl -s -X POST ${SERVICE_URL}/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"text": "我想查询银行卡余额"}'

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
  }' | python3 -m json.tool 2>/dev/null || \
curl -s -X POST ${SERVICE_URL}/predict_batch \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"texts": ["我想买一些基金投资", "我要申请个人贷款", "怎么转账到其他银行"]}'

# 4. 模型信息
echo -e "\n\n💾 4. 模型信息:"
curl -s ${SERVICE_URL}/model_info \
  -H "Host: bert.fyl080801.uk" \
  | python3 -m json.tool 2>/dev/null || \
curl -s ${SERVICE_URL}/model_info -H "Host: bert.fyl080801.uk"

echo -e "\n\n=========================================="
echo "✅ 测试完成"
echo "=========================================="
```

运行测试：
```bash
chmod +x test-external-api.sh
./test-external-api.sh
```

---

## DNS 配置指南

### 1. 在域名管理面板添加 A 记录

```
类型: A
主机记录: bert
记录值: 89.208.241.158
TTL: 600
```

### 2. 验证 DNS 解析

```bash
# 检查 DNS 解析
nslookup bert.fyl080801.uk
# 或
dig bert.fyl080801.uk

# 预期输出
# bert.fyl080801.uk.  IN  A  89.208.241.158
```

### 3. 测试域名访问

```bash
# DNS 生效后测试
curl http://bert.fyl080801.uk/health
```

---

## 网络架构

```
外部用户
    |
    v
DNS: bert.fyl080801.uk -> 89.208.241.158
    |
    v
Ingress Controller (NodePort: 8080)
    |
    v
Ingress Rule (Host: bert.fyl080801.uk)
    |
    v
Service: intent-bert-inference-service:5000
    |
    v
Pod: intent-bert-inference (GPU: RTX 4070 Ti SUPER)
```

---

## 故障排查

### 1. 检查 Ingress 状态

```bash
kubectl get ingress intent-bert-ingress -n dev
kubectl describe ingress intent-bert-ingress -n dev
```

### 2. 检查 Ingress Controller

```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=ingress-nginx
kubectl logs -n kube-system -l app.kubernetes.io/name=ingress-nginx
```

### 3. 测试节点端口连通性

```bash
# 从外部测试
telnet 89.208.241.158 8080
# 或
nc -zv 89.208.241.158 8080
```

### 4. 检查防火墙规则

确保 bandwagon 节点的防火墙允许 8080 端口入站访问。

---

## 注意事项

1. **Host 头必须设置**: 使用公网 IP 访问时，必须在请求头中添加 `Host: bert.fyl080801.uk`
2. **DNS 生效时间**: DNS 修改通常需要 10-60 分钟生效
3. **防火墙**: 确保云服务器安全组开放 8080 端口
4. **HTTPS**: 如需 HTTPS 访问，需要配置 TLS 证书
