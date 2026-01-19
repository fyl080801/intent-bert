"""
多任务BERT模型定义
支持同时预测一级、二级、三级标签
"""

import torch
import torch.nn as nn
from transformers import BertPreTrainedModel, BertModel


class BertForMultiLabelClassification(BertPreTrainedModel):
    """
    BERT多任务分类模型
    同时预测三个层级的标签
    """

    def __init__(self, config, num_level1_labels, num_level2_labels, num_level3_labels):
        super().__init__(config)
        self.num_level1_labels = num_level1_labels
        self.num_level2_labels = num_level2_labels
        self.num_level3_labels = num_level3_labels

        self.bert = BertModel(config)

        # Dropout层
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

        # 三个独立的分类头
        self.level1_classifier = nn.Linear(config.hidden_size, num_level1_labels)
        self.level2_classifier = nn.Linear(config.hidden_size, num_level2_labels)
        self.level3_classifier = nn.Linear(config.hidden_size, num_level3_labels)

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
        r"""
        labels (:obj:`dict`, `optional`):
            包含三个层级标签的字典:
                - level1: 一级标签 (batch_size,)
                - level2: 二级标签 (batch_size,)
                - level3: 三级标签 (batch_size,)
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

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

        # 通过三个分类头
        logits_level1 = self.level1_classifier(pooled_output)
        logits_level2 = self.level2_classifier(pooled_output)
        logits_level3 = self.level3_classifier(pooled_output)

        if not return_dict:
            return (logits_level1, logits_level2, logits_level3)

        return {
            'logits_level1': logits_level1,
            'logits_level2': logits_level2,
            'logits_level3': logits_level3,
        }


class BertForHierarchicalClassification(BertPreTrainedModel):
    """
    BERT层级分类模型
    考虑标签之间的层级关系
    一级 -> 二级 -> 三级
    """

    def __init__(self, config, num_level1_labels, num_level2_labels, num_level3_labels,
                 level1_to_level2_mapping, level2_to_level3_mapping):
        super().__init__(config)
        self.num_level1_labels = num_level1_labels
        self.num_level2_labels = num_level2_labels
        self.num_level3_labels = num_level3_labels

        # 层级映射
        self.level1_to_level2_mapping = level1_to_level2_mapping
        self.level2_to_level3_mapping = level2_to_level3_mapping

        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

        # 层级分类器（使用父标签信息）
        self.level1_classifier = nn.Linear(config.hidden_size, num_level1_labels)

        # 二级分类器：考虑一级标签
        self.level2_classifier = nn.Linear(config.hidden_size + num_level1_labels,
                                           num_level2_labels)

        # 三级分类器：考虑一级和二级标签
        self.level3_classifier = nn.Linear(config.hidden_size + num_level1_labels + num_level2_labels,
                                           num_level3_labels)

        self.post_init()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        labels=None,
        return_dict=None,
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            return_dict=return_dict,
        )

        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)

        # 一级分类
        logits_level1 = self.level1_classifier(pooled_output)
        level1_probs = torch.softmax(logits_level1, dim=-1)

        # 二级分类（使用一级标签信息）
        level2_input = torch.cat([pooled_output, level1_probs], dim=-1)
        logits_level2 = self.level2_classifier(level2_input)

        # 三级分类（使用一级和二级标签信息）
        level2_probs = torch.softmax(logits_level2, dim=-1)
        level3_input = torch.cat([pooled_output, level1_probs, level2_probs], dim=-1)
        logits_level3 = self.level3_classifier(level3_input)

        return {
            'logits_level1': logits_level1,
            'logits_level2': logits_level2,
            'logits_level3': logits_level3,
        }


def create_multitask_model(model_name, num_level1, num_level2, num_level3):
    """
    创建多任务BERT模型的辅助函数

    Args:
        model_name: 预训练模型名称
        num_level1: 一级标签数量
        num_level2: 二级标签数量
        num_level3: 三级标签数量

    Returns:
        model: BertForMultiLabelClassification实例
    """
    from transformers import BertConfig

    config = BertConfig.from_pretrained(model_name)
    model = BertForMultiLabelClassification.from_pretrained(
        model_name,
        config=config,
        num_level1_labels=num_level1,
        num_level2_labels=num_level2,
        num_level3_labels=num_level3
    )

    return model
