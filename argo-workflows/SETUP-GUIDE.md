# BERT训练与部署工作流 - 快速配置指南

## 📋 概述

本工作流实现以下功能：
- ✅ 从GitHub拉取源码：https://github.com/fyl080801/intent-bert.git
- ✅ 支持选择Git分支
- ✅ CUDA训练支持（runtimeClass: nvidia）
- ✅ PVC挂载训练数据（训练集、验证集、配置）
- ✅ hostPath存储模型下载缓存和训练结果
- ✅ 训练完成后构建推理服务镜像
- ✅ 推送镜像到私有仓库：192.168.68.95:31443/ai-apps/intent-bert
- ✅ 命名空间：dev

## 🔧 代理配置

工作流已配置代理用于下载模型：
- HTTPS_PROXY: `http://192.168.68.95:25041`
- HTTP_PROXY: `http://192.168.68.95:25041`

如果需要修改代理，可以：

```bash
# 方式1: 命令行参数
argo submit bert-training-and-deployment.yaml \
  --namespace dev \
  -p https_proxy=http://your-proxy:port \
  -p http_proxy=http://your-proxy:port

# 方式2: 编辑参数文件
vim workflow-params-example.yaml
# 修改 https_proxy 和 http_proxy 的值
```

## 🚀 快速开始

### 方式1: 使用快速启动脚本（推荐）

```bash
cd argo-workflows
./quick-start.sh
```

### 方式2: 手动配置

#### 1. 创建命名空间

```bash
kubectl create namespace dev
```

#### 2. 创建RuntimeClass（GPU支持）

```bash
kubectl apply -f - << EOF
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
  namespace: dev
handler: nvidia
EOF
```

#### 3. 创建PVC（训练数据存储）

```bash
kubectl apply -f - << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bert-training-data-pvc
  namespace: dev
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 10Gi
EOF
```

#### 4. 创建Docker Registry Secret

```bash
kubectl create secret docker-registry docker-registry-secret \
  --docker-server=192.168.68.95:31443 \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  -n dev
```

#### 5. 提交工作流

```bash
cd argo-workflows
argo submit bert-training-and-deployment.yaml --namespace dev
```

## 📝 自定义参数

```bash
# 使用命令行参数
argo submit bert-training-and-deployment.yaml \
  --namespace dev \
  -p branch=feature/test \
  -p batch_size=32 \
  -p num_epochs=10 \
  -p image_tag=v1.0.0

# 使用参数文件
argo submit bert-training-and-deployment.yaml \
  --namespace dev \
  --parameter-file workflow-params-example.yaml
```

## 📊 监控工作流

```bash
# 实时监控
argo watch <workflow-name> -n dev

# 查看日志
argo logs <workflow-name> -n dev

# 查看Pod
kubectl get pods -n dev -l workflows.argoproj.io/workflow=<workflow-name>
```

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `bert-training-and-deployment.yaml` | 主工作流定义 |
| `k8s-supporting-resources.yaml` | Kubernetes资源（PVC、Secret等） |
| `quick-start.sh` | 快速启动脚本 |
| `workflow-params-example.yaml` | 参数配置示例 |
| `SETUP-GUIDE.md` | 本文件 |
| `TRAINING-DEPLOYMENT-GUIDE.md` | 详细使用指南 |

## 🔧 常见问题

### PVC未创建

```bash
kubectl get pvc -n dev
kubectl apply -f k8s-supporting-resources.yaml
```

### GPU不可用

```bash
kubectl get runtimeclass nvidia -n dev
kubectl get nodes -l gpu=true
```

### 镜像推送失败

```bash
kubectl get secret docker-registry-secret -n dev -o yaml
```
