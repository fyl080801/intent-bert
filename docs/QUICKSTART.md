# 快速开始指南

## 5分钟快速部署金融意图BERT分类系统

### 前提条件

- Python 3.10+
- Node.js 18+
- 至少8GB RAM
- （可选）Docker

### 步骤1: 安装依赖

```bash
# 安装Python依赖
pip install -r lib/requirements.txt

# 安装Node.js依赖
npm install
```

### 步骤2: 准备数据

确保您有以下数据文件在`datasets/`目录：
- `datasets/financial_intent_dataset.csv` (训练集)
- `datasets/financial_intent_validation.csv` (验证集)

这些文件已经在datasets目录中。

### 步骤3: 训练模型

```bash
npm run train:model
```

或：

```bash
python lib/python/train.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --output_dir models
```

训练大约需要30-60分钟（取决于硬件）。

### 步骤4: 启动服务

**方式A: 本地开发模式**

```bash
# 终端1: 启动Python模型服务
npm run serve:model

# 终端2: 启动Node.js API服务
npm run dev
```

**方式B: Docker部署**

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 步骤5: 测试API

```bash
# 健康检查
curl http://localhost:3000/health

# 测试预测
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"基金怎么买"}'

# 查看示例
curl http://localhost:3000/api/example
```

### 预期输出

```json
{
  "success": true,
  "data": {
    "label_level1": "投资理财",
    "label_level2": "基金投资",
    "label_level3": "开放式基金",
    "confidence_level1": 0.95,
    "confidence_level2": 0.93,
    "confidence_level3": 0.91,
    "overall_confidence": 0.93
  }
}
```

## 交互式预测

```bash
npm run predict
```

然后输入文本进行预测。

## 常用命令

```bash
# 训练模型
npm run train:model

# 启动模型服务
npm run serve:model

# 启动API服务
npm run dev

# 交互式预测
npm run predict

# 测试模型
npm run test:model

# 构建项目
npm run build

# 启动生产服务
npm start
```

## Docker命令

```bash
# 构建镜像
docker build -t financial-intent-bert .

# 运行容器
docker run -d -p 3000:3000 -p 5000:5000 --name financial-intent financial-intent-bert

# 使用Docker Compose
docker-compose up -d      # 启动
docker-compose logs -f    # 查看日志
docker-compose down       # 停止
```

## 故障排除

### 问题1: 训练时内存不足

```bash
# 减小batch size
python train.py --batch_size 8
```

### 问题2: Python模型服务无法启动

```bash
# 检查模型是否存在
ls model_output/

# 确保已训练模型
npm run train:model
```

### 问题3: Node.js无法连接到Python服务

```bash
# 检查Python服务是否运行
curl http://localhost:5000/health

# 检查环境变量
echo $MODEL_SERVICE_URL
```

## 下一步

- 阅读完整文档: [README_BERT.md](./README_BERT.md)
- 查看数据集说明: [DATASET_README.md](./DATASET_README.md)
- 自定义模型参数: 修改 `train.py` 参数
- 集成到您的应用: 查看 `src/modelClient.ts` 和 `src/server.ts`

## 获取帮助

如果遇到问题，请：
1. 查看日志输出
2. 检查系统要求
3. 查阅完整文档

祝您使用愉快！
