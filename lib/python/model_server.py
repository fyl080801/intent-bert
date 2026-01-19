#!/usr/bin/env python3
"""
金融意图BERT模型推理服务
提供REST API接口
"""

import os
import json
import torch
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import BertTokenizer
from models import BertForMultiLabelClassification
from typing import Dict, List, Union


app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量
predictor = None


class ModelPredictor:
    """模型预测器（单例）"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = None):
        if self._initialized:
            return

        if model_path is None:
            model_path = os.environ.get('MODEL_PATH', 'models')

        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 加载标签编码器
        with open(os.path.join(model_path, 'label_encoders.json'), 'r', encoding='utf-8') as f:
            self.encoders = json.load(f)

        # 创建反向映射
        self.level1_id_to_label = {v: k for k, v in self.encoders['level1']['mapping'].items()}
        self.level2_id_to_label = {v: k for k, v in self.encoders['level2']['mapping'].items()}
        self.level3_id_to_label = {v: k for k, v in self.encoders['level3']['mapping'].items()}

        # 获取标签数量
        num_level1_labels = len(self.encoders['level1']['classes'])
        num_level2_labels = len(self.encoders['level2']['classes'])
        num_level3_labels = len(self.encoders['level3']['classes'])

        # 加载tokenizer和模型
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.model = BertForMultiLabelClassification.from_pretrained(
            model_path,
            num_level1_labels=num_level1_labels,
            num_level2_labels=num_level2_labels,
            num_level3_labels=num_level3_labels
        )
        self.model.to(self.device)
        self.model.eval()

        # 加载配置
        with open(os.path.join(model_path, 'training_config.json'), 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.max_length = self.config.get('max_length', 128)

        self._initialized = True
        print(f"模型已加载: {model_path}")

    def predict(self, text: str) -> Dict[str, Union[str, float]]:
        """预测单条文本"""
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits_l1 = outputs['logits_level1'][0]
        logits_l2 = outputs['logits_level2'][0]
        logits_l3 = outputs['logits_level3'][0]

        pred_l1 = torch.argmax(logits_l1).item()
        pred_l2 = torch.argmax(logits_l2).item()
        pred_l3 = torch.argmax(logits_l3).item()

        prob_l1 = torch.softmax(logits_l1, dim=0)[pred_l1].item()
        prob_l2 = torch.softmax(logits_l2, dim=0)[pred_l2].item()
        prob_l3 = torch.softmax(logits_l3, dim=0)[pred_l3].item()

        return {
            'label_level1': self.level1_id_to_label[pred_l1],
            'label_level2': self.level2_id_to_label[pred_l2],
            'label_level3': self.level3_id_to_label[pred_l3],
            'confidence_level1': round(prob_l1, 4),
            'confidence_level2': round(prob_l2, 4),
            'confidence_level3': round(prob_l3, 4),
            'overall_confidence': round((prob_l1 + prob_l2 + prob_l3) / 3, 4)
        }

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Union[str, float]]]:
        """批量预测"""
        results = []
        for text in texts:
            result = self.predict(text)
            result['text'] = text
            results.append(result)
        return results


def get_predictor():
    """获取预测器实例"""
    global predictor
    if predictor is None:
        model_path = os.environ.get('MODEL_PATH', './model_output')
        predictor = ModelPredictor(model_path)
    return predictor


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': predictor is not None
    })


@app.route('/predict', methods=['POST'])
def predict():
    """
    预测接口

    请求体:
    {
        "text": "用户咨询文本"
    }

    返回:
    {
        "label_level1": "一级标签",
        "label_level2": "二级标签",
        "label_level3": "三级标签",
        "confidence_level1": 0.95,
        "confidence_level2": 0.93,
        "confidence_level3": 0.91,
        "overall_confidence": 0.93
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing "text" field in request'}), 400

        text = data['text']

        if not isinstance(text, str):
            return jsonify({'error': 'Text must be a string'}), 400

        predictor_instance = get_predictor()
        result = predictor_instance.predict(text)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/predict_batch', methods=['POST'])
def predict_batch():
    """
    批量预测接口

    请求体:
    {
        "texts": ["文本1", "文本2", ...]
    }

    返回:
    {
        "results": [...]
    }
    """
    try:
        data = request.get_json()

        if not data or 'texts' not in data:
            return jsonify({'error': 'Missing "texts" field in request'}), 400

        texts = data['texts']

        if not isinstance(texts, list):
            return jsonify({'error': 'Texts must be a list'}), 400

        predictor_instance = get_predictor()
        results = predictor_instance.predict_batch(texts)

        return jsonify({'results': results})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/model_info', methods=['GET'])
def model_info():
    """获取模型信息"""
    predictor_instance = get_predictor()

    return jsonify({
        'model_path': predictor_instance.model_path,
        'device': str(predictor_instance.device),
        'max_length': predictor_instance.max_length,
        'num_labels': {
            'level1': len(predictor_instance.encoders['level1']['classes']),
            'level2': len(predictor_instance.encoders['level2']['classes']),
            'level3': len(predictor_instance.encoders['level3']['classes'])
        },
        'labels': {
            'level1': predictor_instance.encoders['level1']['classes'],
            'level2': predictor_instance.encoders['level2']['classes'],
            'level3': predictor_instance.encoders['level3']['classes'][:10]  # 只显示前10个
        }
    })


if __name__ == '__main__':
    # 初始化预测器
    get_predictor()

    # 启动服务
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"\n启动模型服务...")
    print(f"地址: http://{host}:{port}")
    print(f"健康检查: http://{host}:{port}/health")
    print(f"模型信息: http://{host}:{port}/model_info")
    print(f"预测接口: http://{host}:{port}/predict")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug)
