# BERT 微调 Argo Workflow 快速入门

本指南将帮助你在 5 分钟内启动第一个 BERT 微调工作流。

## 📦 前置准备清单

在开始之前，请确保以下条件已满足：

- [ ] Kubernetes 集群已运行（v1.20+）
- [ ] Argo Workflows 已安装（v3.4+）
- [ ] kubectl 已配置并可以访问集群
- [ ] argo CLI 已安装
- [ ] 所有节点上已创建模型存储目录

## 🚀 快速开始（3步）

### 步骤 1: 准备 Kubernetes 环境

```bash
# 1. 在所有节点上创建模型存储目录
# 在每个节点上执行：
sudo mkdir -p /mnt/models/bert-finetune
sudo chmod 755 /mnt/models/bert-finetune

# 2. 安装 Argo Workflows（如果未安装）
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.4.0/install.yaml

# 3. 验证 Argo 安装
kubectl get pods -n argo

# 4. 配置 Argo CLI（如果需要）
argo server &
export ARGO_SERVER=localhost:2746
export ARGO_INSECURE_SKIP_VERIFY=true
```

### 步骤 2: 准备训练数据

将训练数据放置在可访问的位置：

```bash
# 选项 A: 使用 Git 仓库（推荐用于开发）
git clone https://github.com/your-org/bert-aliyun-test.git
cd bert-aliyun-test/argo-workflows

# 选项 B: 上传数据到 HTTP 服务器
# 然后修改 workflow 中的数据源 URL

# 选项 C: 使用 PVC 挂载数据
# 创建包含数据的 PVC，然后在 workflow 中引用
```

### 步骤 3: 提交工作流

```bash
# 进入工作流目录
cd /path/to/bert-aliyun-test/argo-workflows

# 使用脚本提交（最简单）
./submit-workflow.sh --watch

# 或使用 Argo CLI 直接提交
argo submit bert-finetune-simple.yaml \
  --name bert-finetune-quickstart \
  --watch
```

就这么简单！你的第一个 BERT 微调工作流现在应该正在运行了。

## 📊 监控工作流

### 查看工作流状态

```bash
# 列出所有工作流
argo list

# 查看特定工作流
argo get bert-finetune-quickstart

# 实时监控（推荐）
argo watch bert-finetune-quickstart
```

### 查看日志

```bash
# 查看所有步骤的日志
argo logs bert-finetune-quickstart

# 查看特定步骤的日志
argo logs bert-finetune-quickstart -s train-bert-model

# 实时跟踪日志
argo logs bert-finetune-quickstart -f
```

### 使用 Argo UI

```bash
# 端口转发到本地
kubectl port-forward -n argo svc/argo-server 2746:2746

# 在浏览器中打开
# http://localhost:2746
```

## 🎯 常用场景

### 场景 1: 快速测试（使用 CPU）

```bash
# 使用简化的 workflow，减少训练轮数
./submit-workflow.sh \
  --epochs 1 \
  --batch-size 8 \
  --watch
```

### 场景 2: 生产训练（使用 GPU）

首先修改 `bert-finetune-simple.yaml`，在资源配置中添加 GPU：

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"  # 请求 1 个 GPU
```

然后提交：

```bash
./submit-workflow.sh \
  --batch-size 32 \
  --epochs 10 \
  --watch
```

### 场景 3: 自定义模型

```bash
# 使用不同的预训练模型
./submit-workflow.sh \
  --model hfl/chinese-bert-wwm-ext \
  --learning-rate 3e-5 \
  --watch
```

### 场景 4: 超参数搜索

```bash
# 批量提交多个工作流进行超参数搜索
for lr in 1e-5 2e-5 3e-5 5e-5; do
  ./submit-workflow.sh \
    --learning-rate $lr \
    --name bert-lr-${lr}
done

# 查看所有工作流
argo list | grep bert-lr
```

## 💾 模型输出

训练完成后，模型将保存在所有节点的 `/mnt/models/bert-finetune` 目录。

### 查找模型文件

```bash
# 在任何节点上查看模型文件
ls -lh /mnt/models/bert-finetune/

# 输出应包含：
# - pytorch_model.bin       (模型权重)
# - config.json             (模型配置)
# - tokenizer.json          (分词器)
# - training_config.json    (训练配置)
# - eval_results.json       (评估结果)
# - label_encoders.json     (标签编码器)
```

### 复制模型到其他位置

```bash
# 复制到安全的位置
sudo cp -r /mnt/models/bert-finetune /opt/models/bert-finetune-$(date +%Y%m%d)

# 或打包备份
cd /mnt/models
tar czf bert-finetune-$(date +%Y%m%d).tar.gz bert-finetune
```

## 🛠️ 故障排查

### 问题 1: 工作流提交失败

```bash
# 检查 Argo 连接
argo version

# 检查命名空间
kubectl get namespace

# 查看详细错误
argo submit bert-finetune-simple.yaml --verbose
```

### 问题 2: Pod 处于 Pending 状态

```bash
# 查看 Pod 详情
kubectl describe pod -l workflows.argoproj.io/workflow=<workflow-name>

# 常见原因：
# - 资源不足：减少 batch_size 或增加集群资源
# - 镜像拉取失败：检查镜像名称和仓库凭证
# - 节点选择器：确保有匹配的节点
```

### 问题 3: 训练失败

```bash
# 查看容器日志
kubectl logs -l workflows.argoproj.io/workflow=<workflow-name> -c train-bert-model

# 常见原因：
# - 数据文件未找到：检查数据路径配置
# - 内存不足：减少 batch_size
# - CUDA 错误：检查 GPU 可用性和驱动
```

### 问题 4: 权限错误

```bash
# 检查 hostPath 目录权限
ls -ld /mnt/models/bert-finetune

# 修复权限
sudo chmod 755 /mnt/models/bert-finetune
sudo chown -R 1000:1000 /mnt/models/bert-finetune
```

## 📚 下一步

- 📖 阅读 [完整文档](README.md) 了解更多配置选项
- 🔧 查看 [Kubernetes 配置示例](k8s-configs.yaml) 进行生产部署
- 🎨 参考 [完整版 Workflow](bert-finetune-workflow.yaml) 实现高级功能
- 💡 探索 Argo Workflow 的其他功能：
  - [参数优化](https://argoproj.github.io/argo-workflows/node-field-ref/)
  - [CronWorkflow](https://argoproj.github.io/argo-workflows/cron-workflows/)
  - [工作流模板](https://argoproj.github.io/argo-workflows/workflow-templates/)

## 🔗 有用的命令

```bash
# 查看工作流历史
argo list -l workflows.argoproj.io/workflow-template=bert-finetune

# 重试失败的工作流
argo retry <workflow-name>

# 终止运行中的工作流
argo terminate <workflow-name>

# 删除已完成的工作流
argo delete <workflow-name>

# 批量删除旧工作流
argo delete --older-than 24h  # 删除24小时前的工作流

# 查看工作流统计
argo list --chunk-size 50
```

## 💡 最佳实践

1. **资源管理**
   - 始终设置合理的资源请求和限制
   - 使用 ResourceQuota 防止资源耗尽
   - 监控集群资源使用情况

2. **数据管理**
   - 使用版本控制管理数据集
   - 在 workflow 中验证数据完整性
   - 考虑使用专门的数据存储（S3、NFS等）

3. **模型管理**
   - 为每个工作流生成唯一的模型输出路径
   - 保留训练配置和评估结果
   - 定期备份训练好的模型

4. **监控和日志**
   - 使用 Argo UI 进行可视化监控
   - 集成 Prometheus/Grafana 进行深度监控
   - 保留日志以便后续分析

5. **安全性**
   - 使用 Secret 管理敏感信息
   - 限制 ServiceAccount 权限
   - 定期更新镜像和依赖

## 🆘 获取帮助

- 📖 [Argo Workflows 官方文档](https://argoproj.github.io/argo-workflows/)
- 💬 [Argo Slack 社区](https://argoproj.github.io/community/)
- 🐛 [报告问题](https://github.com/argoproj/argo-workflows/issues)
- 📧 联系项目维护者

祝你使用愉快！🎉
