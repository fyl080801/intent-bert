# 数据集同步到 Kubernetes PVC 指南

## 概述

本指南说明如何将本地数据集同步到 Kubernetes 集群的 PVC 存储卷，以便在 Argo Workflow 中使用。

## 前提条件

- 已配置 `kubectl` 并可访问 Kubernetes 集群
- PVC `bert-training-data-pvc` 已存在
- 本地数据集文件已准备好

## 快速开始

### 方法 1: 使用同步脚本（推荐）

```bash
# 同步所有增量训练数据集
./scripts/sync-data-to-pvc.sh

# 或指定要同步的文件/目录
./scripts/sync-data-to-pvc.sh \
  datasets/financial_intent_incremental_v1 \
  datasets/financial_intent_incremental_v2 \
  datasets/dataset_registry.json
```

### 方法 2: 手动同步

```bash
# 1. 创建临时 Pod
kubectl run data-sync -n dev \
  --image=busybox:1.36 \
  --restart=Never \
  --command -- sleep 3600

# 2. 挂载 PVC
kubectl delete pod data-sync -n dev --grace-period=0 &>/dev/null || true

kubectl run data-sync -n dev \
  --image=busybox:1.36 \
  --restart=Never \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "data-sync",
      "image": "busybox:1.36",
      "command": ["sh", "-c", "sleep 3600"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "bert-training-data-pvc"
      }
    }]
  }
}'

# 3. 等待 Pod 就绪
kubectl wait --for=condition=ready pod/data-sync -n dev --timeout=60s

# 4. 同步文件（使用 tar）
# 同步单个目录
tar czf - datasets/financial_intent_incremental_v1 | \
  kubectl exec -i -n dev data-sync -- tar xzf - -C /data

# 5. 验证
kubectl exec -n dev data-sync -- ls -lh /data/datasets/

# 6. 清理
kubectl delete pod data-sync -n dev
```

## 当前需要同步的数据

### 增量训练数据集

```bash
./scripts/sync-data-to-pvc.sh \
  datasets/financial_intent_incremental_v1 \
  datasets/financial_intent_incremental_v2
```

### 更新的数据集注册表

```bash
./scripts/sync-data-to-pvc.sh \
  datasets/dataset_registry.json
```

### 完整同步（推荐）

同步所有修改过的数据：

```bash
./scripts/sync-data-to-pvc.sh \
  datasets/financial_intent_incremental_v1 \
  datasets/financial_intent_incremental_v2 \
  datasets/financial_intent_fixed \
  datasets/dataset_registry.json
```

## 验证同步结果

### 检查文件是否存在

```bash
# 创建临时 Pod 检查
kubectl run check-pod -n dev --rm -it --restart=Never \
  --image=busybox:1.36 \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "check-pod",
      "image": "busybox:1.36",
      "command": ["sh"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "bert-training-data-pvc"
      }
    }]
  }
}' -- ls -lhR /data/datasets/
```

### 检查数据集注册表

```bash
kubectl run check-registry -n dev --rm -it --restart=Never \
  --image=busybox:1.36 \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "check-registry",
      "image": "busybox:1.36",
      "command": ["sh"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "bert-training-data-pvc"
      }
    }]
  }
}' -- cat /data/datasets/dataset_registry.json
```

## PVC 挂载信息

根据 Argo Workflow 配置：

```yaml
- name: training-data-pvc
  persistentVolumeClaim:
    claimName: "bert-training-data-pvc"
```

在工作流容器中挂载为：
- **容器路径**: `/data`
- **访问模式**: ReadOnlyMany (ROX)
- **存储类型**: NFS

## 环境变量配置

如果需要使用不同的配置：

```bash
# 指定命名空间
export NAMESPACE="dev"

# 指定 PVC 名称
export PVC_NAME="bert-training-data-pvc"

# 指定挂载路径
export MOUNT_PATH="/data"

# 运行同步脚本
./scripts/sync-data-to-pvc.sh datasets/...
```

## 常见问题

### Q1: PVC 是只读的，为什么能同步？

A: `bert-training-data-pvc` 的访问模式是 ROX (ReadOnlyMany)，但这只是限制了 Pod 的挂载方式。我们可以：
1. 通过单个读写访问的 Pod 同步数据
2. 或在 PVC 配置允许的情况下直接写入

### Q2: 同步速度慢怎么办？

A: 使用 tar 压缩传输可以显著提高速度：

```bash
# 优点：
# - 减少文件传输次数
# - 压缩数据减少传输量
# - 保持文件权限和属性

# 脚本已自动使用 tar 传输
```

### Q3: 如何确认数据已同步？

A: 使用工作流验证：

```bash
# 提交一个简单的测试工作流
kubectl create -f <(argo submit \
  --name test-data-access \
  --from argo-workflows/bert-training-universal.yaml \
  -p dataset_name="financial_intent_incremental_v1" \
  -p output_suffix="test-001")
```

### Q4: 数据文件很大，如何避免重复同步？

A: 脚本使用 tar 覆盖模式，已存在的文件会被更新。为避免重复同步：

```bash
# 1. 先检查文件是否存在
kubectl exec -n dev data-sync -- ls /data/datasets/financial_intent_incremental_v1/train.csv

# 2. 只同步修改过的文件
./scripts/sync-data-to-pvc.sh \
  datasets/dataset_registry.json  # 只同步注册表
```

## 自动化工作流

### Git Hook 自动同步

创建 `.git/hooks/post-commit`:

```bash
#!/bin/bash
# 在提交后自动同步数据集到 PVC

CHANGED_DATASETS=$(git diff --name-only HEAD~1 HEAD | grep "^datasets/")

if [ -n "$CHANGED_DATASETS" ]; then
    echo "检测到数据集变更，开始同步到 PVC..."

    ./scripts/sync-data-to-pvc.sh $CHANGED_DATASETS

    echo "✓ 数据集已同步到 PVC"
fi
```

### CI/CD 集成

在 CI/CD 流程中添加数据同步步骤：

```yaml
# .github/workflows/sync-data.yml
name: Sync Data to Cluster

on:
  push:
    paths:
      - 'datasets/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Sync to Kubernetes
        run: |
          kubectl config use-context your-cluster
          ./scripts/sync-data-to-pvc.sh datasets/
```

## 监控和维护

### 查看 PVC 使用情况

```bash
kubectl exec -n dev any-running-pod -- df -h /data
```

### 清理旧数据

```bash
# 通过临时 Pod 清理
kubectl run cleanup-pod -n dev --rm -it --restart=Never \
  --image=busybox:1.36 \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "cleanup-pod",
      "image": "busybox:1.36",
      "command": ["sh"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "bert-training-data-pvc"
      }
    }]
  }
}' -- rm -rf /data/datasets/old_version
```

## 总结

1. ✅ 使用 `sync-data-to-pvc.sh` 脚本简化同步过程
2. ✅ 同步后验证文件存在性
3. ✅ 通过测试工作流确认数据可访问
4. ✅ 设置自动化流程减少手动操作
