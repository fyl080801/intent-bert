# Argo Workflow for BERT Fine-Tuning

本目录包含用于在 Kubernetes 上运行 BERT 模型微调的 Argo Workflow 配置文件。

## 📋 目录

- [工作流概述](#工作流概述)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [存储配置](#存储配置)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)

## 🎯 工作流概述

`bert-finetune-workflow.yaml` 定义了一个完整的 BERT 模型微调流水线，包含以下步骤：

```
┌─────────────────────────────────────────────────────────────┐
│                    BERT Fine-Tuning Pipeline                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Data Preparation      - 下载和验证训练数据                │
│  2. Build Docker Image    - 构建训练容器镜像（可选）           │
│  3. Train BERT Model      - 执行模型微调                      │
│  4. Validate Model        - 验证模型输出和评估指标             │
│  5. Export Model          - 导出模型到S3（可选）              │
│  6. Cleanup               - 清理临时文件                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 前置要求

### 1. Kubernetes 集群配置

确保你的 Kubernetes 集群已安装以下组件：

```bash
# 检查 Argo Workflows 是否已安装
kubectl get pods -n argo

# 如果未安装，执行：
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.4.0/install.yaml
```

### 2. 存储配置

工作流使用 **hostPath** 将模型持久化到节点本地路径：

```yaml
# 在 workflow 中配置的路径
host_model_path: "/mnt/models/bert-finetune"  # Node 本地路径
container_model_path: "/app/models"           # 容器内路径
```

**重要**: 确保所有 Kubernetes 节点上存在该目录：

```bash
# 在所有节点上创建模型存储目录
sudo mkdir -p /mnt/models/bert-finetune
sudo chmod 777 /mnt/models/bert-finetune

# 或者使用更安全的权限
sudo chown -R 1000:1000 /mnt/models/bert-finetune
sudo chmod 755 /mnt/models/bert-finetune
```

### 3. 容器镜像

推送 Docker 镜像到你的镜像仓库：

```bash
# 修改 Dockerfile 中的镜像地址
# 然后构建并推送
docker build -t registry.example.com/bert-finetune:latest .
docker push registry.example.com/bert-finetune:latest
```

### 4. 数据准备

将训练数据上传到可访问的存储位置（HTTP/S3/Git等）：

```bash
# 示例：使用 HTTP 服务器
python3 -m http.server 8000 --directory datasets/

# 或上传到 S3
aws s3 sync datasets/ s3://your-bucket/datasets/
```

## 🚀 快速开始

### 方法1: 使用 Argo CLI 提交工作流

```bash
# 提交工作流
argo submit bert-finetune-workflow.yaml \
  --name bert-finetune-$(date +%Y%m%d-%H%M%S) \
  -p train_data_path="datasets/financial_intent_dataset.csv" \
  -p val_data_path="datasets/financial_intent_validation.csv" \
  -p batch_size="16" \
  -p num_epochs="5" \
  -p learning_rate="2e-5" \
  -p host_model_path="/mnt/models/bert-finetune"

# 查看工作流状态
argo get @latest

# 查看工作流日志
argo logs @latest

# 查看工作流可视化
argo watch @latest
```

### 方法2: 使用 kubectl 提交工作流

```bash
# 直接提交
kubectl apply -f bert-finetune-workflow.yaml

# 查看工作流列表
kubectl get workflows

# 查看特定工作流详情
kubectl describe workflow bert-finetune-workflow
```

### 方法3: 通过 Argo UI 提交

1. 访问 Argo UI: `http://argo-server.argo.svc.cluster.local:2746`
2. 点击 "Submit New Workflow"
3. 上传或粘贴 `bert-finetune-workflow.yaml`
4. 调整参数（可选）
5. 点击 "Submit"

## ⚙️ 配置说明

### 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `train_data_path` | `datasets/financial_intent_dataset.csv` | 训练数据路径 |
| `val_data_path` | `datasets/financial_intent_validation.csv` | 验证数据路径 |
| `model_name` | `bert-base-chinese` | 预训练模型名称 |
| `batch_size` | `16` | 批次大小 |
| `num_epochs` | `5` | 训练轮数 |
| `learning_rate` | `2e-5` | 学习率 |
| `max_length` | `128` | 最大序列长度 |
| `warmup_steps` | `500` | 预热步数 |
| `weight_decay` | `0.01` | 权重衰减 |
| `host_model_path` | `/mnt/models/bert-finetune` | Node 本地模型存储路径 |
| `container_model_path` | `/app/models` | 容器内模型路径 |

### 资源配置

根据你的集群资源配置资源限制：

```yaml
resources:
  requests:
    memory: "8Gi"      # 最小内存需求
    cpu: "4000m"       # 最小CPU需求
  limits:
    memory: "16Gi"     # 最大内存限制
    cpu: "8000m"       # 最大CPU限制
```

**GPU 配置**（如果集群有 GPU）：

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"  # 请求1个GPU
```

## 💾 存储配置

### HostPath 配置

工作流使用 hostPath 将模型持久化到节点本地：

```yaml
volumes:
  - name: host-models
    hostPath:
      path: "/mnt/models/bert-finetune"  # 确保此路径在所有节点上存在
      type: DirectoryOrCreate              # 自动创建目录

volumeMounts:
  - name: host-models
    mountPath: "/app/models"              # 容器内挂载点
```

### 模型输出目录结构

训练完成后，模型将保存在 hostPath 指定的目录：

```
/mnt/models/bert-finetune/
├── pytorch_model.bin              # 模型权重
├── config.json                    # 模型配置
├── tokenizer.json                 # 分词器配置
├── training_config.json           # 训练参数和结果
├── eval_results.json              # 评估指标
├── label_encoders.json            # 标签编码器映射
├── logs/                          # 训练日志
│   └── events.out.tfevents.*
└── checkpoint-*                   # 检查点（如果启用）
```

## 📊 监控与日志

### 查看工作流状态

```bash
# 列出所有工作流
argo list

# 查看特定工作流
argo get <workflow-name>

# 实时监控工作流
argo watch <workflow-name>
```

### 查看日志

```bash
# 查看所有步骤的日志
argo logs <workflow-name>

# 查看特定步骤的日志
argo logs <workflow-name> -s train-model

# 实时跟踪日志
argo logs <workflow-name> -f
```

### 查看训练进度

```bash
# 进入运行的容器
kubectl exec -it <pod-name> -- /bin/bash

# 查看训练日志
tail -f /app/models/logs/training.log

# 查看GPU使用情况（如果有GPU）
nvidia-smi

# 查看进程
ps aux | grep python
```

## 🔍 故障排查

### 常见问题

#### 1. hostPath 权限问题

**错误**: `permission denied: /mnt/models/bert-finetune`

**解决方案**:
```bash
# 在所有节点上修复权限
sudo mkdir -p /mnt/models/bert-finetune
sudo chown -R 1000:1000 /mnt/models/bert-finetune
sudo chmod 755 /mnt/models/bert-finetune
```

#### 2. 镜像拉取失败

**错误**: `ImagePullBackOff`

**解决方案**:
```bash
# 确认镜像存在
docker pull registry.example.com/bert-finetune:latest

# 如果使用私有仓库，创建 imagePullSecret
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=<username> \
  --docker-password=<password>

# 在 workflow 中引用
spec:
  templates:
    - container:
        imagePullSecrets:
          - name: regcred
```

#### 3. 资源不足

**错误**: `Insufficient cpu/memory`

**解决方案**:
```bash
# 检查集群资源
kubectl describe nodes

# 调整 workflow 中的资源请求
# 减少 batch_size 或使用更小的模型
```

#### 4. 数据文件未找到

**错误**: `File not found: datasets/financial_intent_dataset.csv`

**解决方案**:
```bash
# 确认数据文件路径正确
# 检查 volumeMounts 是否正确配置
# 验证数据文件已成功下载到容器内
```

#### 5. 训练速度慢

**优化方案**:
- 增加 `batch_size`（如果内存允许）
- 减少 `max_length`（如果不需要很长的序列）
- 使用 GPU：在 resources 中添加 `nvidia.com/gpu: "1"`
- 增加训练节点的资源限制

### 调试技巧

```bash
# 启用详细日志
argo submit bert-finetune-workflow.yaml --verbose

# 查看工作流事件
kubectl get events --sort-by='.lastTimestamp'

# 查看Pod详情
kubectl describe pod <pod-name>

# 进入失败的容器调试
kubectl debug -it <pod-name> --image=nicolaka/netshoot -- sh
```

## 📝 高级用法

### 自定义工作流

创建自定义参数文件 `params.yaml`:

```yaml
train_data_path: "datasets/custom_train.csv"
val_data_path: "datasets/custom_val.csv"
batch_size: "32"
num_epochs: "10"
learning_rate: "3e-5"
model_name: "hfl/chinese-bert-wwm-ext"
```

提交时使用：

```bash
argo submit -f params.yaml bert-finetune-workflow.yaml
```

### 定时训练

使用 CronWorkflow 创建定时训练任务：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  name: bert-finetune-scheduled
spec:
  schedule: "0 2 * * 6"  # 每周六凌晨2点执行
  workflowSpec:
    # ... 从 bert-finetune-workflow.yaml 复制 spec 内容
```

### 参数优化

使用 Argo Workflow 的参数网格搜索进行超参数优化：

```yaml
# 在 workflow 中添加
withItems:
  - batch_size: ["16", "32", "64"]
  - learning_rate: ["1e-5", "2e-5", "3e-5"]
```

## 🔗 相关资源

- [Argo Workflows 官方文档](https://argoproj.github.io/argo-workflows/)
- [BERT 模型微调指南](../docs/QUICKSTART.md)
- [Docker 构建说明](../README.md)
- [项目主文档](../README.md)

## 📞 支持

如有问题，请提交 Issue 或联系项目维护者。
