# BERT训练与部署工作流使用指南

这个目录包含用于BERT微调和推理服务部署的Argo Workflows定义。

## 📋 目录

- [架构概述](#架构概述)
- [前置条件](#前置条件)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [执行工作流](#执行工作流)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)

## 🏗️ 架构概述

工作流包含以下主要步骤：

```
┌─────────────────────────────────────────────────────────────┐
│                    BERT训练与部署Pipeline                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌──────────────────┐   ┌─────────────┐
│ 1. 拉取源码    │   │ 2. 准备训练数据   │   │ 3. 安装依赖  │
│ Git Checkout  │   │   PVC挂载        │   │ pip install │
└───────────────┘   └──────────────────┘   └─────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ 4. BERT模型训练  │
                    │ - CUDA支持      │
                    │ - hostPath缓存  │
                    │ - PVC数据       │
                    └──────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌──────────────┐   ┌──────────────┐
            │ 5. 模型验证  │   │ 6. 构建镜像   │
            │ 检查输出文件  │   │ Kaniko Build │
            └──────────────┘   └──────────────┘
                                      │
                              ┌───────┴────────┐
                              ▼                ▼
                      ┌──────────────┐  ┌──────────────┐
                      │ 7. 部署验证  │  │ 8. 清理资源   │
                      │ 验证镜像推送  │  │ 删除临时文件  │
                      └──────────────┘  └──────────────┘
```

### 关键特性

1. **源码管理**：从Git仓库拉取代码，支持分支和指定commit
2. **GPU支持**：使用`runtimeClass: nvidia`启用CUDA支持
3. **存储策略**：
   - 训练数据：通过PVC挂载（train/validation/config）
   - 模型下载缓存：使用节点本地hostPath
   - 训练输出：使用节点本地hostPath
4. **镜像构建**：使用Kaniko在容器内构建并推送到私有仓库
5. **自动化部署**：构建完成后自动部署到Kubernetes

## 📦 前置条件

### 1. Kubernetes集群配置

确保集群已安装以下组件：

```bash
# 检查Argo Workflows
kubectl get pods -n argo

# 检查NVIDIA设备插件（如果使用GPU）
kubectl get pods -n kube-system | grep nvidia

# 检查StorageClass
kubectl get storageclass
```

### 2. 节点准备

在需要运行训练任务的节点上创建目录：

```bash
# 在每个训练节点上执行
sudo mkdir -p /mnt/models/cache
sudo mkdir -p /mnt/models/bert-output
sudo chmod 777 /mnt/models/cache
sudo chmod 777 /mnt/models/bert-output

# 为GPU节点打标签
kubectl label nodes <gpu-node> gpu=true
```

### 3. 准备训练数据PVC

上传训练数据到PVC：

```bash
# 创建一个临时Pod来上传数据
kubectl run --rm -it --restart=Never data-uploader --image=alpine --sh

# 在Pod内执行（假设已通过kubectl cp上传）
# mkdir -p /data/datasets
# cd /data/datasets
# <上传你的CSV文件>
```

或者使用`kubectl cp`：

```bash
# 创建临时Pod
kubectl run data-pod --image=alpine --restart=Never -it --command -- sh

# 在另一个终端，复制数据
kubectl cp datasets/financial_intent_dataset.csv data-pod:/data/datasets/
kubectl cp datasets/financial_intent_validation.csv data-pod:/data/datasets/
kubectl cp datasets/dataset_labels_info.json data-pod:/data/datasets/

# 删除临时Pod
kubectl delete pod data-pod
```

### 4. 配置Docker镜像仓库认证

创建Docker registry secret：

```bash
kubectl create secret docker-registry docker-registry-secret \
  --docker-server=192.168.68.95:31443 \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  --docker-email=<your-email> \
  -n default
```

### 5. 部署支持性资源

```bash
# 部署所有Kubernetes资源
kubectl apply -f k8s-supporting-resources.yaml

# 验证资源创建
kubectl get pvc,secret,configmap,runtimeclass -l app=bert-finetune
```

## 🚀 快速开始

### 1. 使用默认参数执行

```bash
# 提交工作流
argo submit bert-training-and-deployment.yaml \
  --name bert-training-$(date +%Y%m%d-%H%M%S) \
  --watch
```

### 2. 自定义参数执行

```bash
# 提交工作流并自定义参数
argo submit bert-training-and-deployment.yaml \
  --name bert-training-custom \
  -p repo_url=https://github.com/your-org/bert-aliyun-test.git \
  -p branch=feature/upgrade \
  -p model_name=bert-base-chinese \
  -p batch_size=32 \
  -p num_epochs=10 \
  -p learning_rate=3e-5 \
  -p image_registry=192.168.68.95:31443 \
  -p image_repository=ai-apps/intent-bert \
  -p image_tag=v1.0.0 \
  --watch
```

## ⚙️ 配置说明

### 工作流参数

| 参数名称 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `repo_url` | string | Git仓库URL | 源码仓库地址 |
| `branch` | string | `main` | Git分支名称 |
| `git_revision` | string | `""` | Git commit/revision（覆盖branch） |
| `pvc_name` | string | `bert-training-data-pvc` | 训练数据PVC名称 |
| `pvc_train_data_path` | string | 训练集PVC路径 | 训练数据文件路径 |
| `pvc_val_data_path` | string | 验证集PVC路径 | 验证数据文件路径 |
| `pvc_config_path` | string | 配置文件PVC路径 | 标签配置文件路径 |
| `model_name` | string | `bert-base-chinese` | 预训练模型名称 |
| `batch_size` | string | `16` | 训练批次大小 |
| `num_epochs` | string | `5` | 训练轮数 |
| `learning_rate` | string | `2e-5` | 学习率 |
| `max_length` | string | `128` | 最大序列长度 |
| `warmup_steps` | string | `500` | 预热步数 |
| `weight_decay` | string | `0.01` | 权重衰减 |
| `host_model_download_path` | string | `/mnt/models/cache` | 节点模型缓存路径 |
| `host_model_output_path` | string | `/mnt/models/bert-output` | 节点输出路径 |
| `image_registry` | string | `192.168.68.95:31443` | 镜像仓库地址 |
| `image_repository` | string | `ai-apps/intent-bert` | 镜像仓库名称 |
| `image_tag` | string | `latest` | 镜像标签 |

### 存储路径说明

1. **训练数据（PVC）**：
   - 只读挂载，多个Pod可以同时访问
   - 路径：`/data/datasets/`

2. **模型下载缓存（hostPath）**：
   - 读写挂载，训练Pod可读写
   - 预训练模型下载后缓存在此
   - 路径：`/app/.cache/models` (容器) → `/mnt/models/cache` (节点)

3. **训练输出（hostPath）**：
   - 读写挂载，训练结果保存在此
   - 路径：`/app/models` (容器) → `/mnt/models/bert-output` (节点)

## 📊 执行工作流

### 基本命令

```bash
# 提交工作流
argo submit bert-training-and-deployment.yaml

# 列出工作流
argo list

# 查看工作流状态
argo get <workflow-name>

# 实时监控工作流
argo watch <workflow-name>

# 查看工作流日志
argo logs <workflow-name>

# 查看特定步骤日志
argo logs <workflow-name> -l step=train-model

# 删除工作流
argo delete <workflow-name>
```

## 🔧 故障排查

### 常见问题

#### 1. Git拉取失败

```bash
# 错误: cannot clone repository
# 解决: 检查Git凭证
kubectl get secret git-ssh-key -o yaml

# 或使用HTTPS token
argo submit bert-training-and-deployment.yaml \
  -p repo_url=https://<token>@github.com/your-org/bert-aliyun-test.git
```

#### 2. PVC挂载失败

```bash
# 错误: persistentvolumeclaim "bert-training-data-pvc" not found
# 解决: 创建PVC
kubectl apply -f k8s-supporting-resources.yaml

# 检查PVC状态
kubectl get pvc bert-training-data-pvc
kubectl describe pvc bert-training-data-pvc
```

#### 3. GPU不可用

```bash
# 错误: CUDA not available
# 解决: 检查GPU节点和RuntimeClass
kubectl get runtimeclass nvidia
kubectl get nodes -l gpu=true

# 检查节点GPU资源
kubectl describe node <gpu-node> | grep nvidia.com/gpu
```

#### 4. 镜像构建失败

```bash
# 错误: cannot push to registry
# 解决: 检查Docker registry凭证
kubectl get secret docker-registry-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d

# 测试镜像仓库连接
docker login 192.168.68.95:31443
docker pull alpine:latest
docker tag alpine:latest 192.168.68.95:31443/test/alpine:latest
docker push 192.168.68.95:31443/test/alpine:latest
```

## 📝 最佳实践

### 1. 参数管理

- 使用ConfigMap管理默认参数
- 为不同环境创建不同的参数文件
- 使用Git commit hash作为镜像标签

### 2. 资源管理

- 根据实际需要调整资源限制
- 使用PriorityClass确保训练任务优先级
- 配置节点亲和性，在GPU节点运行训练

### 3. 数据管理

- 定期清理过期的模型文件
- 使用Snapshot备份重要的训练结果
- 建立数据版本管理机制
