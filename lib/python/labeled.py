import pandas as pd
import json
import time
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional, Dict, List
import torch

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'labeling_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class OpenSourceLabeler:
    """基于开源模型的数据标注工具"""
    
    SUPPORTED_MODELS = {
        # 推荐模型（按效果和资源需求排序）
        'qwen2.5-7b': {
            'model_name': 'Qwen/Qwen2.5-7B-Instruct',
            'min_vram': '16GB',
            'quality': '优秀',
            'speed': '快'
        },
        'qwen2.5-14b': {
            'model_name': 'Qwen/Qwen2.5-14B-Instruct',
            'min_vram': '28GB',
            'quality': '优秀',
            'speed': '中'
        },
        'qwen2.5-32b': {
            'model_name': 'Qwen/Qwen2.5-32B-Instruct',
            'min_vram': '60GB',
            'quality': '卓越',
            'speed': '慢'
        },
        'glm-4-9b': {
            'model_name': 'THUDM/glm-4-9b-chat',
            'min_vram': '20GB',
            'quality': '良好',
            'speed': '快'
        },
        'internlm2.5-7b': {
            'model_name': 'internlm/internlm2_5-7b-chat',
            'min_vram': '16GB',
            'quality': '良好',
            'speed': '快'
        },
        'baichuan2-13b': {
            'model_name': 'baichuan-inc/Baichuan2-13B-Chat',
            'min_vram': '28GB',
            'quality': '良好',
            'speed': '中'
        },
        'mistral-7b': {
            'model_name': 'mistralai/Mistral-7B-Instruct-v0.3',
            'min_vram': '16GB',
            'quality': '中等（英文优秀）',
            'speed': '快'
        },
        'llama3.1-8b': {
            'model_name': 'meta-llama/Meta-Llama-3.1-8B-Instruct',
            'min_vram': '18GB',
            'quality': '中等（英文优秀）',
            'speed': '快'
        }
    }
    
    def __init__(self, model_type='qwen2.5-7b', device='cuda', quantization=None,
                 use_vllm=False, vllm_config=None):
        """
        初始化标注器
        
        Args:
            model_type: 模型类型，见SUPPORTED_MODELS
            device: 运行设备 ('cuda' 或 'cpu')
            quantization: 量化方式 (None, '8bit', '4bit')
            use_vllm: 是否使用vLLM加速（推荐批量处理）
            vllm_config: vLLM配置字典
        """
        self.model_type = model_type
        self.device = device
        self.use_vllm = use_vllm
        
        if model_type not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model_type}. 支持: {list(self.SUPPORTED_MODELS.keys())}")
        
        model_info = self.SUPPORTED_MODELS[model_type]
        self.model_name = model_info['model_name']
        
        logging.info(f"初始化模型: {model_type} ({self.model_name})")
        logging.info(f"最低显存要求: {model_info['min_vram']}")
        
        # 检查GPU可用性
        if device == 'cuda' and not torch.cuda.is_available():
            logging.warning("CUDA不可用，切换到CPU模式")
            self.device = 'cpu'
        
        # 加载模型
        if use_vllm:
            self._init_vllm_model(vllm_config or {})
        else:
            self._init_transformers_model(quantization)
    
    def _init_transformers_model(self, quantization):
        """使用transformers加载模型"""
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        
        logging.info("使用transformers加载模型...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        # 量化配置
        load_kwargs = {'trust_remote_code': True}
        
        if quantization == '8bit':
            logging.info("使用8bit量化")
            load_kwargs['load_in_8bit'] = True
            load_kwargs['device_map'] = 'auto'
        elif quantization == '4bit':
            logging.info("使用4bit量化")
            load_kwargs['quantization_config'] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            load_kwargs['device_map'] = 'auto'
        else:
            if self.device == 'cuda':
                load_kwargs['device_map'] = 'auto'
                load_kwargs['torch_dtype'] = torch.float16
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            **load_kwargs
        )
        
        self.model.eval()
        logging.info("模型加载完成")
    
    def _init_vllm_model(self, vllm_config):
        """使用vLLM加载模型（推荐批量处理）"""
        try:
            from vllm import LLM, SamplingParams
            
            logging.info("使用vLLM加载模型（高性能模式）...")
            
            default_config = {
                'tensor_parallel_size': 1,
                'gpu_memory_utilization': 0.9,
                'max_model_len': 2048,
                'trust_remote_code': True
            }
            default_config.update(vllm_config)
            
            self.vllm_model = LLM(model=self.model_name, **default_config)
            self.sampling_params = SamplingParams(
                temperature=0.7,
                top_p=0.8,
                max_tokens=1000
            )
            
            logging.info("vLLM模型加载完成")
            
        except ImportError:
            logging.error("vLLM未安装，请运行: pip install vllm")
            raise
    
    def label_text(self, text: str, retry: int = 2) -> Dict:
        """
        标注单条文本
        
        Args:
            text: 待标注文本
            retry: 重试次数
            
        Returns:
            标注结果字典
        """
        prompt = self._build_prompt(text)
        
        for attempt in range(retry):
            try:
                if self.use_vllm:
                    result = self._generate_vllm(prompt)
                else:
                    result = self._generate_transformers(prompt)
                
                # 解析结果
                parsed = self._parse_result(result)
                if parsed:
                    return parsed
                    
            except Exception as e:
                logging.warning(f"标注失败 (尝试 {attempt+1}/{retry}): {e}")
                if attempt < retry - 1:
                    time.sleep(1)
        
        # 失败返回默认值
        return self._get_default_labels()
    
    def label_batch(self, texts: List[str]) -> List[Dict]:
        """
        批量标注（vLLM模式下更高效）
        
        Args:
            texts: 文本列表
            
        Returns:
            标注结果列表
        """
        if not self.use_vllm:
            # 非vLLM模式逐条处理
            return [self.label_text(text) for text in texts]
        
        # vLLM批量处理
        prompts = [self._build_prompt(text) for text in texts]
        
        try:
            outputs = self.vllm_model.generate(prompts, self.sampling_params)
            results = []
            
            for output in outputs:
                generated_text = output.outputs[0].text
                parsed = self._parse_result(generated_text)
                results.append(parsed if parsed else self._get_default_labels())
            
            return results
            
        except Exception as e:
            logging.error(f"批量标注失败: {e}")
            return [self._get_default_labels() for _ in texts]
    
    def _build_prompt(self, text: str) -> str:
        """构建提示词"""
        return f"""你是一个专业的文本分类标注助手。请对以下文本进行详细分析和分类。

文本内容：
{text}

请按照以下JSON格式返回标注结果（只返回JSON，不要其他内容）：
{{
  "label_level1": "一级分类（如：客服咨询、商品评价、技术支持、投诉建议等）",
  "label_level2": "二级分类（在一级分类基础上细分）",
  "label_level3": "三级分类（最细粒度的分类）",
  "intent_complexity": "简单/中等/复杂",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "confidence_score": 0.95
}}

要求：
1. 标签要准确，三级标签要有明确的层级关系
2. intent_complexity只能是：简单、中等、复杂
3. keywords提取3-5个核心关键词
4. confidence_score范围0-1，表示标注的置信度

请直接返回JSON格式的结果："""
    
    def _generate_transformers(self, prompt: str) -> str:
        """使用transformers生成"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        if self.device == 'cuda':
            inputs = inputs.to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1000,
                temperature=0.7,
                top_p=0.8,
                do_sample=True
            )
        
        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 提取生成部分（去除prompt）
        if prompt in result:
            result = result.split(prompt)[-1].strip()
        
        return result
    
    def _generate_vllm(self, prompt: str) -> str:
        """使用vLLM生成（单条）"""
        outputs = self.vllm_model.generate([prompt], self.sampling_params)
        return outputs[0].outputs[0].text
    
    def _parse_result(self, result: str) -> Optional[Dict]:
        """解析模型输出"""
        try:
            # 清理markdown代码块
            result = result.strip()
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0].strip()
            elif '```' in result:
                result = result.split('```')[1].split('```')[0].strip()
            
            # 尝试找到JSON部分
            if '{' in result and '}' in result:
                start = result.find('{')
                end = result.rfind('}') + 1
                result = result[start:end]
            
            parsed = json.loads(result)
            
            # 验证必需字段
            required = ['label_level1', 'label_level2', 'label_level3',
                       'intent_complexity', 'keywords', 'confidence_score']
            
            if all(k in parsed for k in required):
                return parsed
            
        except Exception as e:
            logging.debug(f"解析失败: {e}, 原文: {result[:200]}")
        
        return None
    
    def _get_default_labels(self) -> Dict:
        """默认标签"""
        return {
            'label_level1': '未分类',
            'label_level2': '未分类',
            'label_level3': '未分类',
            'intent_complexity': '中等',
            'keywords': [],
            'confidence_score': 0.5
        }
    
    def process_dataset(self, input_file: str, output_file: Optional[str] = None,
                       text_column: str = 'text', batch_size: int = 10,
                       start_idx: int = 0, end_idx: Optional[int] = None,
                       vllm_batch_size: int = 8):
        """
        处理数据集
        
        Args:
            input_file: 输入CSV文件
            output_file: 输出CSV文件
            text_column: 文本列名
            batch_size: 保存间隔
            start_idx: 起始索引
            end_idx: 结束索引
            vllm_batch_size: vLLM批处理大小
        """
        # 读取数据
        logging.info(f"读取数据: {input_file}")
        df = pd.read_csv(input_file)
        
        if text_column not in df.columns:
            raise ValueError(f"未找到列: {text_column}")
        
        # 输出文件
        if output_file is None:
            output_file = Path(input_file).stem + "_labeled.csv"
        
        # 初始化列
        for col in ['id', 'text', 'label_level1', 'label_level2', 'label_level3',
                    'text_length', 'intent_complexity', 'sample_type',
                    'keywords', 'confidence_score']:
            if col not in df.columns:
                df[col] = None
        
        if df['id'].isna().any():
            df['id'] = range(len(df))
        
        if text_column != 'text':
            df['text'] = df[text_column]
        
        df['text_length'] = df['text'].astype(str).str.len()
        
        if df['sample_type'].isna().all():
            df['sample_type'] = 'train'
        
        # 处理范围
        if end_idx is None:
            end_idx = len(df)
        
        total = end_idx - start_idx
        logging.info(f"处理范围: {start_idx} 到 {end_idx} (共{total}条)")
        
        # 使用vLLM批量处理
        if self.use_vllm:
            self._process_with_vllm_batch(df, start_idx, end_idx, 
                                         vllm_batch_size, batch_size, output_file)
        else:
            self._process_sequential(df, start_idx, end_idx, 
                                    batch_size, output_file)
        
        # 最终保存
        df.to_csv(output_file, index=False)
        logging.info(f"✅ 完成！结果: {output_file}")
        
        self._print_statistics(df)
        
        return df
    
    def _process_with_vllm_batch(self, df, start_idx, end_idx, 
                                  vllm_batch_size, save_batch_size, output_file):
        """vLLM批量处理"""
        for batch_start in range(start_idx, end_idx, vllm_batch_size):
            batch_end = min(batch_start + vllm_batch_size, end_idx)
            
            # 获取批次文本
            batch_texts = []
            batch_indices = []
            
            for idx in range(batch_start, batch_end):
                if pd.isna(df.loc[idx, 'label_level1']) or df.loc[idx, 'label_level1'] == '':
                    batch_texts.append(str(df.loc[idx, 'text']))
                    batch_indices.append(idx)
            
            if not batch_texts:
                continue
            
            # 批量标注
            logging.info(f"处理批次: {batch_start}-{batch_end}")
            results = self.label_batch(batch_texts)
            
            # 更新数据
            for idx, result in zip(batch_indices, results):
                df.loc[idx, 'label_level1'] = result['label_level1']
                df.loc[idx, 'label_level2'] = result['label_level2']
                df.loc[idx, 'label_level3'] = result['label_level3']
                df.loc[idx, 'intent_complexity'] = result['intent_complexity']
                df.loc[idx, 'keywords'] = ','.join(result['keywords']) if isinstance(result['keywords'], list) else str(result['keywords'])
                df.loc[idx, 'confidence_score'] = result['confidence_score']
            
            # 定期保存
            if (batch_end) % save_batch_size == 0:
                df.to_csv(output_file, index=False)
                logging.info(f"已保存: {batch_end}/{end_idx}")
    
    def _process_sequential(self, df, start_idx, end_idx, batch_size, output_file):
        """顺序处理"""
        for idx in range(start_idx, end_idx):
            if pd.notna(df.loc[idx, 'label_level1']) and df.loc[idx, 'label_level1'] != '':
                continue
            
            text = str(df.loc[idx, 'text'])
            result = self.label_text(text)
            
            df.loc[idx, 'label_level1'] = result['label_level1']
            df.loc[idx, 'label_level2'] = result['label_level2']
            df.loc[idx, 'label_level3'] = result['label_level3']
            df.loc[idx, 'intent_complexity'] = result['intent_complexity']
            df.loc[idx, 'keywords'] = ','.join(result['keywords']) if isinstance(result['keywords'], list) else str(result['keywords'])
            df.loc[idx, 'confidence_score'] = result['confidence_score']
            
            logging.info(f"[{idx+1}/{end_idx}] {result['label_level1']} > {result['label_level2']}")
            
            if (idx + 1) % batch_size == 0:
                df.to_csv(output_file, index=False)
                logging.info(f"已保存: {idx+1}/{end_idx}")
    
    def _print_statistics(self, df):
        """打印统计"""
        logging.info("\n" + "="*50)
        logging.info("数据集统计")
        logging.info("="*50)
        logging.info(f"总数: {len(df)}")
        logging.info(f"\n一级标签:\n{df['label_level1'].value_counts()}")
        logging.info(f"\n复杂度:\n{df['intent_complexity'].value_counts()}")
        logging.info(f"\n平均置信度: {df['confidence_score'].mean():.3f}")
        logging.info("="*50)


def main():
    """使用示例"""
    
    # ============ 配置 ============
    INPUT_FILE = "raw_data.csv"
    OUTPUT_FILE = "labeled_data.csv"
    TEXT_COLUMN = "text"
    
    # 模型选择（推荐qwen2.5-7b，效果好且资源需求适中）
    MODEL_TYPE = 'qwen2.5-7b'  # 可选: qwen2.5-7b, qwen2.5-14b, glm-4-9b 等
    
    # 量化选项（减少显存占用）
    QUANTIZATION = '4bit'  # None, '8bit', '4bit'
    
    # 是否使用vLLM（批量处理推荐，速度快3-5倍）
    USE_VLLM = False  # 需要先安装: pip install vllm
    
    BATCH_SIZE = 10
    VLLM_BATCH_SIZE = 16  # vLLM批处理大小
    # ==============================
    
    try:
        # 创建标注器
        labeler = OpenSourceLabeler(
            model_type=MODEL_TYPE,
            device='cuda',
            quantization=QUANTIZATION,
            use_vllm=USE_VLLM
        )
        
        # 处理数据
        df = labeler.process_dataset(
            input_file=INPUT_FILE,
            output_file=OUTPUT_FILE,
            text_column=TEXT_COLUMN,
            batch_size=BATCH_SIZE,
            vllm_batch_size=VLLM_BATCH_SIZE
        )
        
        print("\n✅ 标注完成！")
        
    except Exception as e:
        logging.error(f"执行出错: {e}")
        raise


if __name__ == "__main__":
    main()