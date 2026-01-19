# 金融意图BERT分类API - Swagger文档

## 📚 API文档访问

### Swagger UI 交互式文档

服务启动后，访问以下地址查看完整的交互式API文档：

```
http://localhost:3000/api-docs
```

### 文档特性

- ✅ **交互式测试** - 直接在浏览器中测试API
- ✅ **完整示例** - 每个接口都包含请求/响应示例
- ✅ **参数说明** - 详细的参数类型、格式、限制说明
- ✅ **在线调试** - 无需额外工具即可发送请求

## 🚀 快速开始

### 1. 启动服务

```bash
# 终端1: 启动Python模型服务
MODEL_PATH=models PORT=5001 ./venv/bin/python lib/python/model_server.py

# 终端2: 启动Node.js API服务
npm run dev
```

### 2. 访问API文档

在浏览器中打开：
```
http://localhost:3000/api-docs
```

### 3. 测试API

在Swagger UI中：

1. **展开接口** - 点击任意接口查看详情
2. **点击 "Try it out"** - 启用交互模式
3. **输入参数** - 填写请求体参数
4. **点击 "Execute"** - 执行请求并查看结果

## 📖 API端点

### 健康检查
```
GET /health
```
检查API服务状态

### 单条预测
```
POST /api/predict
Content-Type: application/json

{
  "text": "我想买一些基金，有什么推荐的吗？"
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "label_level1": "投资理财",
    "label_level2": "基金投资",
    "label_level3": "开放式基金",
    "confidence_level1": 0.9479,
    "confidence_level2": 0.827,
    "confidence_level3": 0.086,
    "overall_confidence": 0.6203
  }
}
```

### 批量预测
```
POST /api/predict-batch
Content-Type: application/json

{
  "texts": [
    "基金怎么买",
    "我想申请贷款",
    "怎么转账"
  ]
}
```

### 模型信息
```
GET /api/model-info
```
获取模型支持的标签列表和配置信息

### 预测示例
```
GET /api/example
```
查看预设示例的预测结果

## 🏷️ 标签层级结构

模型支持三级标签分类：

### 一级标签 (6类)
- 投资理财
- 信贷服务
- 账户服务
- 交易服务
- 产品咨询
- 风险合规

### 二级标签 (24类)
基金投资、股票投资、理财产品、保险规划、个人贷款、企业贷款、信用卡服务、开户注销、密码管理、转账汇款、支付缴费、产品对比、收益计算、风险评估等

### 三级标签 (108类)
开放式基金、指数基金、A股交易、港股通、房贷、消费贷、办卡申请、个人开户、跨行转账、水电煤缴费等

## 🔧 使用cURL测试

### 单条预测
```bash
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"我想买一些基金，有什么推荐的吗？"}'
```

### 批量预测
```bash
curl -X POST http://localhost:3000/api/predict-batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "基金怎么买",
      "我想申请贷款",
      "怎么转账"
    ]
  }'
```

### 获取模型信息
```bash
curl http://localhost:3000/api/model-info
```

## 📝 请求参数说明

### 单条预测 (POST /api/predict)

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 待预测的文本，最大长度512字符 |

### 批量预测 (POST /api/predict-batch)

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| texts | array | 是 | 待预测的文本数组，最多100条，每条最大512字符 |

## 📊 响应字段说明

### PredictionResult

| 字段 | 类型 | 说明 |
|------|------|------|
| label_level1 | string | 一级分类标签 |
| label_level2 | string | 二级分类标签 |
| label_level3 | string | 三级分类标签 |
| confidence_level1 | float | 一级标签置信度 (0-1) |
| confidence_level2 | float | 二级标签置信度 (0-1) |
| confidence_level3 | float | 三级标签置信度 (0-1) |
| overall_confidence | float | 综合置信度，三级平均 |

## ⚠️ 错误处理

所有错误响应格式：
```json
{
  "success": false,
  "error": "错误信息描述"
}
```

常见错误码：
- `400` - 请求参数错误（缺少必需参数、参数类型错误）
- `500` - 服务器内部错误（模型服务异常、推理失败）

## 🔗 相关文件

- **OpenAPI规范**: `swagger.yaml` - 可导入到Postman、Insomnia等工具
- **API服务器**: `src/server.ts` - Express服务实现
- **测试脚本**: `test_api.js` - 自动化测试脚本
- **模型客户端**: `src/modelClient.ts` - API客户端封装

## 📌 Docker部署

```bash
# 构建镜像
docker build -t financial-intent-bert .

# 运行容器
docker run -p 3000:3000 -p 5001:5001 financial-intent-bert

# 访问文档
http://localhost:3000/api-docs
```

## 💡 最佳实践

1. **输入长度** - 建议输入文本长度在10-200字符之间以获得最佳效果
2. **批量处理** - 批量预测适合处理大量文本，但建议每批不超过50条
3. **置信度阈值** - 建议设置置信度阈值（如0.6）过滤低置信度预测
4. **错误重试** - 实现指数退避的重试机制处理临时故障
5. **缓存结果** - 对相同文本可以缓存预测结果以提升性能

## 📧 技术支持

如有问题，请查看：
- 项目README: `README.md`
- 训练文档: `docs/🎉 Training Completed Successfully!.md`
- 数据集标签: `datasets/dataset_labels_info.json`
