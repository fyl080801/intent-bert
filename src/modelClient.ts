/**
 * 金融意图BERT模型客户端
 * 调用Python模型服务API
 */

import axios, { AxiosInstance } from 'axios';

export interface PredictionResult {
  label_level1: string;
  label_level2: string;
  label_level3: string;
  confidence_level1: number;
  confidence_level2: number;
  confidence_level3: number;
  overall_confidence: number;
}

export interface BatchPredictionResult {
  results: Array<PredictionResult & { text: string }>;
}

export interface ModelInfo {
  model_path: string;
  device: string;
  max_length: number;
  num_labels: {
    level1: number;
    level2: number;
    level3: number;
  };
  labels: {
    level1: string[];
    level2: string[];
    level3: string[];
  };
}

export class FinancialIntentClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:5000') {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string; model_loaded: boolean }> {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`健康检查失败: ${this.getErrorMsg(error)}`);
    }
  }

  /**
   * 获取模型信息
   */
  async getModelInfo(): Promise<ModelInfo> {
    try {
      const response = await this.client.get('/model_info');
      return response.data;
    } catch (error) {
      throw new Error(`获取模型信息失败: ${this.getErrorMsg(error)}`);
    }
  }

  /**
   * 预测单条文本
   * @param text 用户咨询文本
   * @returns 预测结果
   */
  async predict(text: string): Promise<PredictionResult> {
    try {
      const response = await this.client.post('/predict', { text });
      return response.data;
    } catch (error) {
      throw new Error(`预测失败: ${this.getErrorMsg(error)}`);
    }
  }

  /**
   * 批量预测
   * @param texts 文本数组
   * @returns 预测结果数组
   */
  async predictBatch(texts: string[]): Promise<BatchPredictionResult> {
    try {
      const response = await this.client.post('/predict_batch', { texts });
      return response.data;
    } catch (error) {
      throw new Error(`批量预测失败: ${this.getErrorMsg(error)}`);
    }
  }

  /**
   * 格式化预测结果
   */
  formatPrediction(result: PredictionResult, text?: string): string {
    const lines = [
      text ? `文本: ${text}` : '',
      `一级标签: ${result.label_level1} (置信度: ${(result.confidence_level1 * 100).toFixed(2)}%)`,
      `二级标签: ${result.label_level2} (置信度: ${(result.confidence_level2 * 100).toFixed(2)}%)`,
      `三级标签: ${result.label_level3} (置信度: ${(result.confidence_level3 * 100).toFixed(2)}%)`,
      `整体置信度: ${(result.overall_confidence * 100).toFixed(2)}%`,
    ].filter(Boolean);

    return lines.join('\n');
  }

  /**
   * 检查服务是否可用
   */
  async isServiceReady(): Promise<boolean> {
    try {
      const result = await this.healthCheck();
      return result.status === 'healthy' && result.model_loaded;
    } catch {
      return false;
    }
  }

  /**
   * 等待服务就绪
   * @param maxWait 最大等待时间（毫秒）
   * @param interval 检查间隔（毫秒）
   */
  async waitForService(maxWait: number = 60000, interval: number = 1000): Promise<void> {
    const start = Date.now();

    while (Date.now() - start < maxWait) {
      if (await this.isServiceReady()) {
        return;
      }
      await this.sleep(interval);
    }

    throw new Error('服务启动超时');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private getErrorMsg(error: unknown): string {
    if (axios.isAxiosError(error)) {
      return error.response?.data?.error || error.message;
    }
    if (error instanceof Error) {
      return error.message;
    }
    return '未知错误';
  }
}

// 导出单例实例
export const modelClient = new FinancialIntentClient(
  process.env.MODEL_SERVICE_URL || 'http://localhost:5000'
);
