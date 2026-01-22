# BERT 推理服务部署完成总结

## 部署架构

```
外部用户
    |
    v
DNS: bert.fyl080801.uk -> 89.208.241.158 (bandwagon 公网 IP)
    |
    v
Ingress Controller (NodePort 8080)
    - 节点: homenas (192.168.68.95)
    - Service: ingress-nginx-controller (NodePort: 8080/8443)
    |
    v
Ingress Rule (Host: bert.fyl080801.uk)
    |
    v
Service: intent-bert-inference-service:5000 (ClusterIP)
    |
    v
Pod: intent-bert-inference-7c8d7db78-pkl6p
    - 节点: fyl-workstation (192.168.68.110)
    - GPU: NVIDIA GeForce RTX 4070 Ti SUPER
    - 模型: financial_intent_fixed-600e8423-73dd-47e4-9a50-067ecd484a0a
```

---

## 服务端点

### 1. 通过 NodePort 直接访问（当前可用）

```bash
http://192.168.68.110:30500
```

### 2. 通过 Ingress + 域名访问（推荐）

**域名**: `bert.fyl080801.uk`
**公网 IP**: `89.208.241.158` (bandwagon)
**端口**: `8080`

**需要配置**:
1. DNS: bert.fyl080801.uk -> 89.208.241.158
2. 防火墙: bandwagon 节点开放 8080 端口

---

## curl 调用示例

### 方式一：NodePort 直接访问（当前可用）

```bash
# 健康检查
curl http://192.168.68.110:30500/health

# 单条预测
curl -X POST http://192.168.68.110:30500/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "我想查询银行卡余额"
  }'

# 批量预测
curl -X POST http://192.168.68.110:30500/predict_batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["基金怎么买", "我要申请贷款", "怎么转账"]
  }'

# 模型信息
curl http://192.168.68.110:30500/model_info
```

### 方式二：通过域名访问（推荐，需配置）

**DNS 配置**:
```
类型: A
主机记录: bert
记录值: 89.208.241.158
```

**访问方式**:
```bash
# 配置 DNS 后
curl -X POST http://bert.fyl080801.uk/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "我想查询银行卡余额"
  }'
```

**通过公网 IP + Host 头访问**（无需 DNS，需开放防火墙）:
```bash
curl -X POST http://89.208.241.158:8080/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{
    "text": "我想查询银行卡余额"
  }'
```

---

## 响应示例

### 单条预测响应

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

### 批量预测响应

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
      "text": "怎么转账",
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

## 完整测试脚本

```bash
#!/bin/bash

# 方式一：NodePort 访问
BASE_URL="http://192.168.68.110:30500"

# 方式二：域名访问（需配置 DNS）
# BASE_URL="http://bert.fyl080801.uk"

# 方式三：公网 IP + Host 头（需开放防火墙）
# BASE_URL="http://89.208.241.158:8080"
# EXTRA_HEADER='-H "Host: bert.fyl080801.uk"'

echo "BERT 推理服务测试"
echo "服务: $BASE_URL"

# 健康检查
echo -e "\n1. 健康检查:"
curl -s ${BASE_URL}/health ${EXTRA_HEADER} | python3 -m json.tool

# 单条预测
echo -e "\n2. 单条预测:"
curl -s -X POST ${BASE_URL}/predict \
  -H "Content-Type: application/json" ${EXTRA_HEADER} \
  -d '{"text": "我想查询银行卡余额"}' | python3 -m json.tool

# 批量预测
echo -e "\n3. 批量预测:"
curl -s -X POST ${BASE_URL}/predict_batch \
  -H "Content-Type: application/json" ${EXTRA_HEADER} \
  -d '{"texts": ["基金投资", "个人贷款", "转账"]}' | python3 -m json.tool

# 模型信息
echo -e "\n4. 模型信息:"
curl -s ${BASE_URL}/model_info ${EXTRA_HEADER} | python3 -m json.tool
```

---

## 部署的文件

### K8s 配置文件

| 文件 | 说明 |
|------|------|
| `argo-workflows/inference-service.yaml` | 推理服务部署配置 |
| `argo-workflows/bert-ingress.yaml` | Ingress 配置 |

### 文档和脚本

| 文件 | 说明 |
|------|------|
| `DEPLOYMENT_INFO.md` | 详细部署文档 |
| `test-external-api.sh` | 外部访问测试脚本 |
| `test-inference-client.py` | Python 测试客户端 |

---

## 已部署资源

### Deployment
```bash
kubectl get deployment intent-bert-inference -n dev
```

### Service
```bash
kubectl get svc intent-bert-inference-service -n dev
kubectl get svc intent-bert-inference-nodeport -n dev
```

### Ingress
```bash
kubectl get ingress intent-bert-ingress -n dev
```

### Pod
```bash
kubectl get pods -n dev -l app=intent-bert,component=inference
```

---

## 网络配置说明

### 当前可用访问方式

1. **NodePort (推荐)**: `http://192.168.68.110:30500`
   - 直接访问，无需额外配置
   - 适用于内网访问

### 需要额外配置的访问方式

2. **域名访问**: `http://bert.fyl080801.uk`
   - 需要配置 DNS: bert.fyl080801.uk -> 89.208.241.158
   - 需要开放 bandwagon 节点防火墙端口 8080

3. **公网 IP + Host 头**: `http://89.208.241.158:8080`
   - 需要添加 Host 头: `Host: bert.fyl080801.uk`
   - 需要开放 bandwagon 节点防火墙端口 8080

---

## 防火墙配置

### Bandwagon 节点 (89.208.241.158)

需要开放端口 8080:

```bash
# 如果使用 ufw
sudo ufw allow 8080/tcp

# 如果使用 firewalld
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# 如果使用 iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4

# 云服务器安全组也需要添加规则
# 入站规则: TCP 8080 0.0.0.0/0
```

---

## API 端点总览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/predict` | POST | 单条文本预测 |
| `/predict_batch` | POST | 批量文本预测 |
| `/model_info` | GET | 模型信息 |

---

## 故障排查

### 1. 检查服务状态

```bash
# Pod 状态
kubectl get pods -n dev -l app=intent-bert,component=inference

# 服务日志
kubectl logs -n dev -l app=intent-bert,component=inference --tail=50

# Ingress 状态
kubectl get ingress intent-bert-ingress -n dev
```

### 2. 测试连接

```bash
# 测试 NodePort
curl http://192.168.68.110:30500/health

# 测试 Ingress Controller
curl http://192.168.68.95:8080/health -H "Host: bert.fyl080801.uk"

# 从集群内测试
kubectl exec -n dev <pod-name> -- curl http://intent-bert-inference-service:5000/health
```

### 3. 常见问题

**问题**: 外部访问超时
**解决**:
- 检查防火墙规则
- 确认云服务器安全组开放端口
- 检查 DNS 解析

**问题**: Ingress 404
**解决**:
- 确认 Host 头正确
- 检查 Ingress 规则
- 查看 Ingress Controller 日志

**问题**: 预测失败
**解决**:
- 检查模型文件是否正确挂载
- 查看 Pod 日志
- 确认 GPU 可用

---

## 性能指标

- **设备**: NVIDIA GeForce RTX 4070 Ti SUPER
- **单条预测**: ~50-100ms
- **批量预测**: 可同时处理多个请求
- **最大文本长度**: 512 字符
- **推荐批量大小**: 8-16 条
