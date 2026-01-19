"""
动态层级BERT模型
支持可变数量的层级和动态配置的分类头
"""

import torch
import torch.nn as nn
from transformers import BertPreTrainedModel, BertModel
from typing import Dict, List, Optional, Any


class BertForDynamicHierarchicalClassification(BertPreTrainedModel):
    """
    动态层级BERT分类模型
    根据配置自动创建N个分类头，支持任意深度的层级

    特性：
    - 动态数量的分类头（由配置决定）
    - 层级感知：每个子层都会使用父层的信息
    - 支持不规则层级树（不同分支深度不同）
    """

    def __init__(self, config, hierarchy_config: Dict[str, Any]):
        """
        初始化动态层级模型

        Args:
            config: BERT配置
            hierarchy_config: 层级配置字典，包含:
                - num_levels: 层级总数
                - level_sizes: 每层的标签数量列表 [level0_size, level1_size, ...]
        """
        super().__init__(config)

        # 从配置中提取层级信息
        self.num_levels = hierarchy_config['num_levels']
        self.level_sizes = hierarchy_config['level_sizes']

        # BERT主体
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

        # 动态创建N个分类头
        self.classifiers = nn.ModuleList()
        for level_idx, num_labels in enumerate(self.level_sizes):
            if level_idx == 0:
                # 第一层：基础分类器，只使用BERT输出
                classifier = nn.Linear(config.hidden_size, num_labels)
            else:
                # 后续层：拼接父级标签的概率信息
                parent_info_size = sum(self.level_sizes[:level_idx])
                classifier = nn.Linear(
                    config.hidden_size + parent_info_size,
                    num_labels
                )
            self.classifiers.append(classifier)

        # 初始化权重
        self.post_init()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
    ):
        """
        前向传播

        Args:
            input_ids: 输入token IDs [batch_size, seq_length]
            attention_mask: 注意力mask [batch_size, seq_length]
            labels: 可选，标签字典用于计算loss

        Returns:
            包含以下字段的字典:
            - logits: 每层的logits列表
            - probs: 每层的概率列表
            - loss: 总损失（如果提供了labels）
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        # BERT编码
        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        # 获取[CLS] token的输出
        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)

        # 逐层预测，每一层都使用前面层的信息
        all_logits = []
        all_probs = []
        accumulated_info = pooled_output

        for level_idx, classifier in enumerate(self.classifiers):
            # 当前层的logits
            logits = classifier(accumulated_info)
            all_logits.append(logits)

            # 计算概率
            probs = torch.softmax(logits, dim=-1)
            all_probs.append(probs)

            # 为下一层拼接当前层的概率信息（hierarchical特征）
            if level_idx < len(self.classifiers) - 1:
                accumulated_info = torch.cat([accumulated_info, probs], dim=-1)

        # 计算loss（如果提供了labels）
        loss = None
        if labels is not None:
            loss = self._compute_hierarchical_loss(all_logits, labels)

        if not return_dict:
            return (loss, all_logits, all_probs) if loss is not None else (all_logits, all_probs)

        return {
            'loss': loss,
            'logits': all_logits,
            'probs': all_probs
        }

    def _compute_hierarchical_loss(self, all_logits: List[torch.Tensor], labels: torch.Tensor) -> torch.Tensor:
        """
        计算层级分类损失

        Args:
            all_logits: 每层的logits列表
            labels: 标签tensor [batch_size, num_levels] 或类似格式

        Returns:
            总损失
        """
        loss_fct = torch.nn.CrossEntropyLoss()
        total_loss = 0
        valid_count = 0

        # 假设labels是 [batch_size, max_depth] 的tensor
        # 需要根据实际情况调整
        if isinstance(labels, dict):
            # 字典格式: {'level0': tensor, 'level1': tensor, ...}
            for level_idx, logits in enumerate(all_logits):
                level_key = f'level{level_idx}'
                if level_key in labels:
                    level_labels = labels[level_key]
                    if level_labels is not None:
                        level_loss = loss_fct(logits, level_labels)
                        total_loss += level_loss
                        valid_count += 1
        elif isinstance(labels, torch.Tensor):
            # Tensor格式: [batch_size, num_levels]
            batch_size = labels.shape[0]
            for level_idx, logits in enumerate(all_logits):
                if level_idx < labels.shape[1]:
                    level_labels = labels[:, level_idx]
                    # 只处理有效标签（非-1）
                    valid_mask = level_labels >= 0
                    if valid_mask.sum() > 0:
                        valid_logits = logits[valid_mask]
                        valid_labels = level_labels[valid_mask]
                        level_loss = loss_fct(valid_logits, valid_labels)
                        total_loss += level_loss
                        valid_count += 1

        # 平均所有有效层级的loss
        avg_loss = total_loss / valid_count if valid_count > 0 else 0
        return avg_loss

    def predict(self, input_ids, attention_mask=None, return_all_levels=True):
        """
        预测接口

        Args:
            input_ids: 输入token IDs
            attention_mask: 注意力mask
            return_all_levels: 是否返回所有层级的结果

        Returns:
            预测结果字典
        """
        self.eval()
        with torch.no_grad():
            outputs = self.forward(input_ids, attention_mask=attention_mask)
            all_probs = outputs['probs']
            all_logits = outputs['logits']

            # 获取每层的预测
            predictions = []
            confidences = []

            for probs, logits in zip(all_probs, all_logits):
                pred_labels = torch.argmax(probs, dim=-1)
                pred_confs = torch.max(probs, dim=-1)[0]
                predictions.append(pred_labels)
                confidences.append(pred_confs)

            if return_all_levels:
                return {
                    'predictions': predictions,  # List of [batch_size]
                    'confidences': confidences,  # List of [batch_size]
                    'probabilities': all_probs   # List of [batch_size, num_labels]
                }
            else:
                # 只返回最后一层（最细粒度）的预测
                return {
                    'predictions': predictions[-1],
                    'confidences': confidences[-1],
                    'probabilities': all_probs[-1]
                }


class BertForDynamicHierarchicalClassificationV2(BertPreTrainedModel):
    """
    动态层级BERT分类模型 V2
    使用更灵活的父标签信息传递方式

    相比V1的改进：
    - 使用父标签的embedding而非原始概率
    - 支持更复杂的层级关系建模
    """

    def __init__(self, config, hierarchy_config: Dict[str, Any], label_embeddings: Optional[nn.Module] = None):
        """
        初始化V2模型

        Args:
            config: BERT配置
            hierarchy_config: 层级配置
            label_embeddings: 可选的标签embedding层
        """
        super().__init__(config)

        self.num_levels = hierarchy_config['num_levels']
        self.level_sizes = hierarchy_config['level_sizes']

        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

        # 标签embedding（可选）
        self.use_label_embeddings = label_embeddings is not None
        if self.use_label_embeddings:
            self.label_embeddings = label_embeddings
            embedding_dim = label_embeddings.embedding_dim
        else:
            embedding_dim = config.hidden_size

        # 动态创建分类头
        self.classifiers = nn.ModuleList()
        for level_idx, num_labels in enumerate(self.level_sizes):
            if level_idx == 0:
                # 第一层
                classifier = nn.Linear(config.hidden_size, num_labels)
            else:
                # 后续层：使用BERT输出 + 父级embedding
                parent_size = self.level_sizes[level_idx - 1]
                if self.use_label_embeddings:
                    input_size = config.hidden_size + embedding_dim
                else:
                    input_size = config.hidden_size + parent_size
                classifier = nn.Linear(input_size, num_labels)
            self.classifiers.append(classifier)

        self.post_init()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        labels=None,
        return_dict=None,
    ):
        """前向传播 V2"""
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            return_dict=return_dict,
        )

        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)

        all_logits = []
        all_probs = []
        parent_info = None

        for level_idx, classifier in enumerate(self.classifiers):
            if level_idx == 0:
                # 第一层
                logits = classifier(pooled_output)
            else:
                # 后续层：拼接父级信息
                if self.use_label_embeddings and parent_info is not None:
                    # 使用父标签的embedding
                    parent_labels = torch.argmax(all_probs[-1], dim=-1)
                    parent_emb = self.label_embeddings(parent_labels)
                    level_input = torch.cat([pooled_output, parent_emb], dim=-1)
                else:
                    # 使用父标签的概率分布
                    level_input = torch.cat([pooled_output, all_probs[-1]], dim=-1)
                logits = classifier(level_input)

            all_logits.append(logits)
            probs = torch.softmax(logits, dim=-1)
            all_probs.append(probs)

        loss = None
        if labels is not None:
            loss = self._compute_hierarchical_loss(all_logits, labels)

        if not return_dict:
            return (loss, all_logits, all_probs) if loss is not None else (all_logits, all_probs)

        return {
            'loss': loss,
            'logits': all_logits,
            'probs': all_probs
        }

    def _compute_hierarchical_loss(self, all_logits: List[torch.Tensor], labels: torch.Tensor) -> torch.Tensor:
        """计算层级损失"""
        loss_fct = torch.nn.CrossEntropyLoss()
        total_loss = 0
        valid_count = 0

        if isinstance(labels, dict):
            for level_idx, logits in enumerate(all_logits):
                level_key = f'level{level_idx}'
                if level_key in labels and labels[level_key] is not None:
                    level_loss = loss_fct(logits, labels[level_key])
                    total_loss += level_loss
                    valid_count += 1

        return total_loss / valid_count if valid_count > 0 else 0


def create_dynamic_model(model_name: str, hierarchy_config: Dict[str, Any],
                        model_version: str = 'v1') -> BertPreTrainedModel:
    """
    创建动态层级BERT模型的辅助函数

    Args:
        model_name: 预训练模型名称 (如 'bert-base-chinese')
        hierarchy_config: 层级配置字典
        model_version: 模型版本 ('v1' 或 'v2')

    Returns:
        初始化好的模型实例
    """
    from transformers import BertConfig

    config = BertConfig.from_pretrained(model_name)

    if model_version == 'v1':
        model = BertForDynamicHierarchicalClassification.from_pretrained(
            model_name,
            config=config,
            hierarchy_config=hierarchy_config
        )
    elif model_version == 'v2':
        model = BertForDynamicHierarchicalClassificationV2.from_pretrained(
            model_name,
            config=config,
            hierarchy_config=hierarchy_config
        )
    else:
        raise ValueError(f"不支持的模型版本: {model_version}")

    return model


def main():
    """测试函数"""
    # 示例配置
    example_hierarchy = {
        'num_levels': 3,
        'level_sizes': [2, 3, 5]  # Level0: 2类, Level1: 3类, Level2: 5类
    }

    print("测试动态层级模型配置...")
    print(f"层级数: {example_hierarchy['num_levels']}")
    print(f"各层级大小: {example_hierarchy['level_sizes']}")

    print("\n✅ 动态模型类已定义")
    print("使用 create_dynamic_model() 函数创建模型实例")


if __name__ == "__main__":
    main()
