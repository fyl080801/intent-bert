/**
 * Node.js API服务示例
 * 调用Python模型服务并提供REST API
 */

import express, { Request, Response } from 'express';
import cors from 'cors';
import { modelClient, PredictionResult } from './modelClient';

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());

// 健康检查
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'nodejs-api' });
});

// 预测接口
app.post('/api/predict', async (req: Request, res: Response) => {
  try {
    const { text } = req.body;

    if (!text) {
      return res.status(400).json({ error: '缺少text参数' });
    }

    // 调用Python模型服务
    const result = await modelClient.predict(text);

    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    console.error('预测失败:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : '预测失败',
    });
  }
});

// 批量预测接口
app.post('/api/predict-batch', async (req: Request, res: Response) => {
  try {
    const { texts } = req.body;

    if (!Array.isArray(texts)) {
      return res.status(400).json({ error: 'texts参数必须是数组' });
    }

    // 调用Python模型服务
    const result = await modelClient.predictBatch(texts);

    res.json({
      success: true,
      data: result.results,
    });
  } catch (error) {
    console.error('批量预测失败:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : '批量预测失败',
    });
  }
});

// 获取模型信息
app.get('/api/model-info', async (req: Request, res: Response) => {
  try {
    const info = await modelClient.getModelInfo();
    res.json({
      success: true,
      data: info,
    });
  } catch (error) {
    console.error('获取模型信息失败:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : '获取模型信息失败',
    });
  }
});

// 示例接口
app.get('/api/example', async (req: Request, res: Response) => {
  try {
    const examples = [
      '基金怎么买',
      '我想申请贷款',
      '信用卡如何激活',
      '怎么转账',
      '理财产品的收益怎么样',
    ];

    const results = await modelClient.predictBatch(examples);

    res.json({
      success: true,
      data: results.results.map((r, i) => ({
        text: examples[i],
        ...r,
      })),
    });
  } catch (error) {
    console.error('示例预测失败:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : '示例预测失败',
    });
  }
});

// 启动服务器
app.listen(PORT, async () => {
  console.log(`Node.js API服务已启动: http://localhost:${PORT}`);
  console.log(`健康检查: http://localhost:${PORT}/health`);
  console.log(`预测接口: http://localhost:${PORT}/api/predict`);
  console.log(`模型信息: http://localhost:${PORT}/api/model-info`);
  console.log(`示例接口: http://localhost:${PORT}/api/example`);

  // 等待Python模型服务就绪
  console.log('\n等待Python模型服务启动...');
  try {
    await modelClient.waitForService(60000, 2000);
    console.log('✓ Python模型服务已就绪');
  } catch (error) {
    console.error('✗ Python模型服务启动超时');
    console.error('请确保Python模型服务正在运行');
  }
});

export default app;
