#!/usr/bin/env python3
"""
统一BERT推理服务 (V2)
支持单标签、多标签和多级标签的统一推理接口
"""

import os
import json
import torch
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import BertTokenizer, AutoModelForSequenceClassification
from typing import Dict, List, Union, Optional, Any
from pathlib import Path


app = Flask(__name__)
CORS(app)

# 全局预测器实例
predictor = None


class UniversalPredictor:
    """统一预测器 - 支持多种标签类型"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = None):
        if self._initialized:
            return

        self.model_path = model_path or os.environ.get('MODEL_PATH', 'models')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 加载训练配置
        self._load_training_config()

        # 根据任务类型初始化模型
        self.task_type = self.config.get('task_type', 'hierarchical')

        if self.task_type == 'single_label':
            self._init_single_label_model()
        elif self.task_type == 'multi_label':
            self._init_multi_label_model()
        elif self.task_type == 'hierarchical':
            self._init_hierarchical_model()
        else:
            raise ValueError(f"不支持的任务类型: {self.task_type}")

        self._initialized = True
        print(f"✓ 模型已加载: {self.model_path}")
        print(f"  任务类型: {self.task_type}")

    def _load_training_config(self):
        """加载训练配置"""
        config_path = os.path.join(self.model_path, 'training_config.json')
        if not Path(config_path).exists():
            # 尝试旧的配置文件
            config_path = os.path.join(self.model_path, 'training_config.json')

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.max_length = self.config.get('max_length', 128)

    def _init_single_label_model(self):
        """初始化单标签分类模型"""
        self.tokenizer = BertTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_path
        )
        self.model.to(self.device)
        self.model.eval()

        # 加载标签映射（如果存在）
        label_map_path = os.path.join(self.model_path, 'label_encoders.json')
        if Path(label_map_path).exists():
            with open(label_map_path, 'r', encoding='utf-8') as f:
                encoders = json.load(f)
            self.id_to_label = {i: label for i, label in enumerate(
                encoders.get('level0', {}).get('classes', [])
            )}
        else:
            num_labels = self.config.get('num_labels', 2)
            self.id_to_label = {i: f"class_{i}" for i in range(num_labels)}

    def _init_multi_label_model(self):
        """初始化多标签分类模型"""
        # TODO: 实现多标签模型初始化
        raise NotImplementedError("多标签分类尚未实现")

    def _init_hierarchical_model(self):
        """初始化层级分类模型"""
        # 导入层级模型
        try:
            from dynamic_models import BertForDynamicHierarchicalClassification
            self.dynamic_model = True
        except ImportError:
            from models import BertForMultiLabelClassification
            self.dynamic_model = False

        self.tokenizer = BertTokenizer.from_pretrained(self.model_path)

        # 加载标签编码器
        encoder_path = os.path.join(self.model_path, 'label_encoders.json')
        hierarchical_mapping_path = os.path.join(
            self.model_path, 'hierarchical_label_mapping.json'
        )

        if Path(hierarchical_mapping_path).exists():
            # 动态层级模型
            with open(hierarchical_mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            self.level_labels = mapping['level_labels']
            self.num_levels = mapping['config']['num_levels']

            # 创建ID到标签的映射
            self.id_to_label = {}
            for level_idx, labels in self.level_labels.items():
                self.id_to_label[level_idx] = {i: label for i, label in enumerate(labels)}

            # 加载模型
            model_config = {
                'num_levels': self.num_levels,
                'level_sizes': [len(self.level_labels[i]) for i in range(self.num_levels)]
            }
            self.model = BertForDynamicHierarchicalClassification.from_pretrained(
                self.model_path,
                hierarchy_config=model_config
            )
        else:
            # 固定三级模型
            with open(encoder_path, 'r', encoding='utf-8') as f:
                encoders = json.load(f)
            self.level_labels = {}
            self.num_levels = 3
            for level_key in ['level0', 'level1', 'level2']:
                if level_key in encoders:
                    self.level_labels[level_key] = encoders[level_key]['classes']

            self.id_to_label = {}
            for level_key in ['level0', 'level1', 'level2']:
                if level_key in encoders:
                    self.id_to_label[level_key] = {
                        v: k for k, v in encoders[level_key]['mapping'].items()
                    }

            from models import BertForMultiLabelClassification
            self.model = BertForMultiLabelClassification.from_pretrained(
                self.model_path,
                num_level1_labels=len(self.level_labels.get('level0', [])),
                num_level2_labels=len(self.level_labels.get('level1', [])),
                num_level3_labels=len(self.level_labels.get('level2', []))
            )

        self.model.to(self.device)
        self.model.eval()

    def predict(self, text: str) -> Dict[str, Any]:
        """
        统一预测接口

        Args:
            text: 输入文本

        Returns:
            统一格式的预测结果
        """
        if self.task_type == 'single_label':
            return self._predict_single_label(text)
        elif self.task_type == 'hierarchical':
            return self._predict_hierarchical(text)
        else:
            raise ValueError(f"不支持的任务类型: {self.task_type}")

    def _predict_single_label(self, text: str) -> Dict[str, Any]:
        """单标签预测"""
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
            logits = outputs.logits[0]
            probs = torch.softmax(logits, dim=-1)

        pred_id = torch.argmax(probs).item()
        confidence = probs[pred_id].item()

        return {
            'task_type': 'single_label',
            'prediction': {
                'label': self.id_to_label.get(pred_id, f"class_{pred_id}"),
                'label_id': pred_id,
                'confidence': round(confidence, 4)
            },
            'all_probabilities': [
                {
                    'label': self.id_to_label.get(i, f"class_{i}"),
                    'probability': round(probs[i].item(), 4)
                }
                for i in range(len(probs))
            ]
        }

    def _predict_hierarchical(self, text: str) -> Dict[str, Any]:
        """层级标签预测"""
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

        # 处理输出
        if self.dynamic_model or hasattr(outputs, 'get') and 'logits' in outputs:
            # 动态层级模型
            all_logits = outputs['logits'] if isinstance(outputs, dict) else outputs
            predictions = []
            confidences = []

            for level_idx, logits in enumerate(all_logits):
                probs = torch.softmax(logits[0], dim=-1)
                pred_id = torch.argmax(probs).item()
                confidence = probs[pred_id].item()

                level_key = str(level_idx)
                label = self.id_to_label[level_key].get(pred_id, f"unknown_{pred_id}")

                predictions.append({
                    'level': level_idx + 1,
                    'label': label,
                    'label_id': pred_id,
                    'confidence': round(confidence, 4)
                })
                confidences.append(confidence)

            overall_confidence = round(sum(confidences) / len(confidences), 4)

            return {
                'task_type': 'hierarchical',
                'num_levels': len(predictions),
                'prediction': predictions,
                'overall_confidence': overall_confidence
            }
        else:
            # 固定三级模型
            logits_l1 = outputs['logits_level1'][0]
            logits_l2 = outputs['logits_level2'][0]
            logits_l3 = outputs['logits_level3'][0]

            pred_l1 = torch.argmax(logits_l1).item()
            pred_l2 = torch.argmax(logits_l2).item()
            pred_l3 = torch.argmax(logits_l3).item()

            prob_l1 = torch.softmax(logits_l1, dim=0)[pred_l1].item()
            prob_l2 = torch.softmax(logits_l2, dim=0)[pred_l2].item()
            prob_l3 = torch.softmax(logits_l3, dim=0)[pred_l3].item()

            predictions = [
                {
                    'level': 1,
                    'label': self.id_to_label.get('level0', {}).get(pred_l1, "unknown"),
                    'label_id': pred_l1,
                    'confidence': round(prob_l1, 4)
                },
                {
                    'level': 2,
                    'label': self.id_to_label.get('level1', {}).get(pred_l2, "unknown"),
                    'label_id': pred_l2,
                    'confidence': round(prob_l2, 4)
                },
                {
                    'level': 3,
                    'label': self.id_to_label.get('level2', {}).get(pred_l3, "unknown"),
                    'label_id': pred_l3,
                    'confidence': round(prob_l3, 4)
                }
            ]

            return {
                'task_type': 'hierarchical',
                'num_levels': 3,
                'prediction': predictions,
                'overall_confidence': round((prob_l1 + prob_l2 + prob_l3) / 3, 4)
            }

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
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
        predictor = UniversalPredictor(model_path)
    return predictor


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': predictor is not None,
        'task_type': predictor.task_type if predictor else None
    })


@app.route('/predict', methods=['POST'])
def predict():
    """
    统一预测接口

    请求体:
    {
        "text": "用户咨询文本"
    }

    返回 (单标签):
    {
        "task_type": "single_label",
        "prediction": {
            "label": "positive",
            "label_id": 1,
            "confidence": 0.95
        },
        "all_probabilities": [...]
    }

    返回 (层级标签):
    {
        "task_type": "hierarchical",
        "num_levels": 3,
        "prediction": [
            {
                "level": 1,
                "label": "投资理财",
                "label_id": 0,
                "confidence": 0.95
            },
            ...
        ],
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
    """批量预测接口"""
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

    info = {
        'model_path': predictor_instance.model_path,
        'device': str(predictor_instance.device),
        'task_type': predictor_instance.task_type,
        'max_length': predictor_instance.max_length
    }

    if predictor_instance.task_type == 'single_label':
        info['num_labels'] = len(predictor_instance.id_to_label)
        info['labels'] = list(predictor_instance.id_to_label.values())
    elif predictor_instance.task_type == 'hierarchical':
        info['num_levels'] = predictor_instance.num_levels
        info['level_labels'] = {
            f"level{i}": list(predictor_instance.id_to_label.get(str(i), {}).values())
            for i in range(predictor_instance.num_levels)
        }

    return jsonify(info)


if __name__ == '__main__':
    # 初始化预测器
    get_predictor()

    # 启动服务
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"\n{'='*60}")
    print(f"统一BERT推理服务 V2")
    print(f"{'='*60}")
    print(f"地址: http://{host}:{port}")
    print(f"健康检查: http://{host}:{port}/health")
    print(f"模型信息: http://{host}:{port}/model_info")
    print(f"预测接口: http://{host}:{port}/predict")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=debug)
