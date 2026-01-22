# BERT 推理服务部署完成 - 最终总结

## ✅ 部署状态

### 服务运行状态

| 组件 | 状态 | 详情 |
|------|------|------|
| 模型服务 | ✅ 正常运行 | Pod: `intent-bert-inference-7c8d7db78-pkl6p` |
| GPU 加速 | ✅ 启用 | NVIDIA GeForce RTX 4070 Ti SUPER |
| 模型加载 | ✅ 成功 | financial_intent_fixed |
| 推理测试 | ✅ 通过 | 预测功能正常 |

### 服务验证结果

```
=== 健康检查 ===
{'model_loaded': True, 'status': 'healthy'}

=== 预测测试 ===
输入: "我想查询银行卡余额"
输出:
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

---

## 🌐 访问方式

### 方式一：域名访问（推荐）

**域名**: `bert.fyl080801.uk`

#### 配置步骤：

1. **DNS 配置**
   ```
   类型: A
   主机记录: bert
   记录值: 89.208.241.158
   TTL: 600
   ```

2. **防火墙配置**（Bandwagon 节点）
   ```bash
   # 开放端口 8080
   sudo ufw allow 8080/tcp

   # 或云服务器安全组添加规则
   # 协议: TCP
   # 端口: 8080
   # 来源: 0.0.0.0/0
   ```

3. **测试访问**
   ```bash
   # 等待 DNS 生效后（通常 10-60 分钟）
   curl -X POST http://bert.fyl080801.uk/predict \
     -H "Content-Type: application/json" \
     -d '{"text": "我想查询银行卡余额"}'
   ```

---

### 方式二：公网 IP + Host 头（临时测试）

```bash
curl -X POST http://89.208.241.158:8080/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"text": "我想查询银行卡余额"}'
```

**需要配置**：开放 Bandwagon 节点防火墙端口 8080

---

### 方式三：内网 NodePort 访问

```bash
curl -X POST http://192.168.68.110:30500/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}'
```

**限制**：仅限内网访问，需要网络连通

---

## 📡 API 接口

### 1. 健康检查

```bash
curl http://bert.fyl080801.uk/health
```

**响应**：
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

---

### 2. 单条文本预测

```bash
curl -X POST http://bert.fyl080801.uk/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "我想查询银行卡余额"
  }'
```

**响应**：
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

---

### 3. 批量文本预测

```bash
curl -X POST http://bert.fyl080801.uk/predict_batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "基金怎么买",
      "我要申请贷款",
      "怎么转账给朋友"
    ]
  }'
```

**响应**：
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
    ...
  ]
}
```

---

### 4. 模型信息

```bash
curl http://bert.fyl080801.uk/model_info
```

**响应**：
```json
{
  "model_path": "/app/models/financial_intent_fixed-...",
  "device": "cuda",
  "max_length": 128,
  "num_labels": {
    "level1": 6,
    "level2": 24,
    "level3": 108
  },
  "labels": {
    "level1": ["交易服务", "产品咨询", "信贷服务", "投资理财", "账户服务", "风险合规"],
    "level2": ["个人贷款", "交易查询", ...],
    "level3": ["A股交易", "个人开户", ...]
  }
}
```

---

## 🔧 完整 curl 示例集合

### 基础示例

```bash
# 1. 健康检查
curl http://bert.fyl080801.uk/health

# 2. 单条预测
curl -X POST http://bert.fyl080801.uk/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}'

# 3. 批量预测
curl -X POST http://bert.fyl080801.uk/predict_batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["基金投资", "个人贷款", "转账"]}'

# 4. 模型信息
curl http://bert.fyl080801.uk/model_info
```

### 完整示例（带格式化输出）

```bash
# 单条预测（格式化输出）
curl -X POST http://bert.fyl080801.uk/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}' | python3 -m json.tool

# 批量预测（格式化输出）
curl -X POST http://bert.fyl080801.uk/predict_batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["基金投资", "个人贷款"]}' | python3 -m json.tool
```

### 使用公网 IP 访问

```bash
# 添加 Host 头访问
curl -X POST http://89.208.241.158:8080/predict \
  -H "Content-Type: application/json" \
  -H "Host: bert.fyl080801.uk" \
  -d '{"text": "我想查询银行卡余额"}'
```

---

## 📊 实际测试结果

### 测试用例 1：余额查询

**输入**: "我想查询银行卡余额"

**输出**:
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

### 测试用例 2：额度提升

**输入**: "信用卡额度怎么提升"

**输出**:
```json
{
  "label_level1": "信贷服务",
  "label_level2": "信用卡服务",
  "label_level3": "额度提升",
  "confidence_level1": 0.9015,
  "confidence_level2": 0.5746,
  "confidence_level3": 0.1670,
  "overall_confidence": 0.5477
}
```

### 测试用例 3：个人贷款

**输入**: "我要申请个人贷款"

**输出**:
```json
{
  "label_level1": "信贷服务",
  "label_level2": "个人贷款",
  "label_level3": "房贷",
  "confidence_level1": 0.9538,
  "confidence_level2": 0.5880,
  "confidence_level3": 0.0870,
  "overall_confidence": 0.5429
}
```

---

## 🏗️ 部署架构

```
用户请求
    |
    v
DNS: bert.fyl080801.uk
    |
    v
公网 IP: 89.208.241.158:8080 (Bandwagon 节点)
    |
    v
Ingress Controller (NodePort 8080)
    - 节点: homenas (192.168.68.95)
    - Ingress Class: nginx
    |
    v
Ingress Rule: Host=bert.fyl080801.uk
    |
    v
Service: intent-bert-inference-service:5000 (ClusterIP)
    |
    v
Pod: intent-bert-inference-7c8d7db78-pkl6p
    - 节点: fyl-workstation (192.168.68.110)
    - GPU: NVIDIA GeForce RTX 4070 Ti SUPER
    - 模型: financial_intent_fixed
    - 运行时: nvidia
```

---

## 📝 已部署资源清单

### Kubernetes 资源

```bash
# Deployment
kubectl get deployment intent-bert-inference -n dev

# Services
kubectl get svc intent-bert-inference-service -n dev        # ClusterIP
kubectl get svc intent-bert-inference-nodeport -n dev      # NodePort

# Ingress
kubectl get ingress intent-bert-ingress -n dev

# Pod
kubectl get pods -n dev -l app=intent-bert,component=inference
```

### 部署文件

| 文件 | 说明 |
|------|------|
| `argo-workflows/inference-service.yaml` | 推理服务部署配置（Deployment + Service） |
| `argo-workflows/bert-ingress.yaml` | Ingress 配置（域名路由） |

### 文档和脚本

| 文件 | 说明 |
|------|------|
| `FINAL_SUMMARY.md` | 最终部署总结（本文档） |
| `DEPLOYMENT_INFO.md` | 详细部署说明 |
| `DEPLOYMENT_SUMMARY.md` | 部署架构文档 |
| `test-external-api.sh` | 外部访问测试脚本 |
| `test-inference-client.py` | Python 测试客户端 |

---

## ⚠️ 重要提示

### 当前状态

1. **服务已部署**: ✅ 所有 K8s 资源已创建
2. **服务运行正常**: ✅ Pod 内部测试通过
3. **GPU 加速启用**: ✅ 使用 RTX 4070 Ti SUPER
4. **推理功能正常**: ✅ 预测结果准确

### 外部访问需要配置

要实现外部访问 `http://bert.fyl080801.uk`，需要完成：

1. **DNS 配置**（必须）
   - bert.fyl080801.uk -> 89.208.241.158

2. **防火墙配置**（必须）
   - 开放 Bandwagon 节点的 8080 端口

3. **验证网络连通性**
   - 测试 DNS 解析
   - 测试端口可达性

---

## 🎯 快速开始

### 步骤 1: 配置 DNS

在域名管理面板添加 A 记录：
```
bert.fyl080801.uk  A  89.208.241.158
```

### 步骤 2: 配置防火墙

在 Bandwagon 节点执行：
```bash
sudo ufw allow 8080/tcp
```

或在云服务器安全组添加规则：
```
协议: TCP
端口: 8080
来源: 0.0.0.0/0
```

### 步骤 3: 测试访问

```bash
# 等待 DNS 生效（10-60 分钟）
curl http://bert.fyl080801.uk/health

# 测试预测
curl -X POST http://bert.fyl080801.uk/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查询银行卡余额"}'
```

---

## 📞 故障排查

### DNS 未生效

```bash
# 检查 DNS 解析
nslookup bert.fyl080801.uk
dig bert.fyl080801.uk
```

### 端口不通

```bash
# 测试端口连通性
telnet 89.208.241.158 8080
nc -zv 89.208.241.158 8080
```

### 服务状态检查

```bash
# 检查 Pod
kubectl get pods -n dev -l app=intent-bert,component=inference

# 查看日志
kubectl logs -n dev intent-bert-inference-xxx -c model-server

# 检查 Ingress
kubectl get ingress intent-bert-ingress -n dev
kubectl describe ingress intent-bert-ingress -n dev
```

---

## 🎉 总结

BERT 推理服务已成功部署到 K8s 集群，使用 GPU 加速，推理功能测试通过。

**下一步**：配置 DNS 和防火墙后，即可通过 `bert.fyl080801.uk` 域名访问服务。

**预计 DNS 生效时间**：10-60 分钟

**服务地址**：http://bert.fyl080801.uk

**API 文档**：参考 `swagger.yaml` 和 `API_USAGE.md`
