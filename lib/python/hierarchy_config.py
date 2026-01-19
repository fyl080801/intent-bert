"""
层级配置解析器
支持动态多级标签结构的解析和处理
"""

import json
from typing import Dict, List, Set, Any
from pathlib import Path


class HierarchyConfigParser:
    """层级配置解析器，从树形JSON结构中提取层级信息"""

    def __init__(self, config_path: str = None, config_dict: dict = None):
        """
        初始化配置解析器

        Args:
            config_path: JSON配置文件路径
            config_dict: 直接传入配置字典（二选一）
        """
        if config_path:
            self.config_path = config_path
            self.config = self._load_config()
        elif config_dict:
            self.config = config_dict
            self.config_path = None
        else:
            raise ValueError("必须提供 config_path 或 config_dict")

        self.hierarchy_info = self._parse_hierarchy()

    def _load_config(self) -> dict:
        """加载JSON配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_hierarchy(self) -> Dict[str, Any]:
        """
        解析层级树，提取关键信息

        Returns:
            包含以下字段的字典:
            - num_levels: 层级总数
            - max_depth: 最大深度
            - level_sizes: 每层的标签数量列表
            - level_labels: 每层的标签集合 {level: [labels]}
            - parent_to_children: 父子关系映射 {parent: [children]}
            - all_paths: 所有可能的完整路径
        """
        labels = self.config['labels']

        # 数据结构
        level_labels: Dict[int, Set[str]] = {}  # {0: set(), 1: set(), ...}
        parent_to_children: Dict[str, List[str]] = {}  # 父子关系映射
        all_paths: List[List[str]] = []  # 所有可能的完整路径

        def traverse(node: Dict, depth: int, parent_path: List[str]):
            """
            递归遍历树节点

            Args:
                node: 当前节点
                depth: 当前深度
                parent_path: 父路径
            """
            node_name = node['name']
            current_path = parent_path + [node_name]

            # 收集当前层的标签
            if depth not in level_labels:
                level_labels[depth] = set()
            level_labels[depth].add(node_name)

            # 记录父子关系
            if len(parent_path) > 0:
                parent = parent_path[-1]
                if parent not in parent_to_children:
                    parent_to_children[parent] = []
                parent_to_children[parent].append(node_name)

            # 如果是叶子节点，记录完整路径
            children = node.get('children', [])
            if not children or len(children) == 0:
                all_paths.append(current_path)
            else:
                # 递归处理子节点
                for child in children:
                    traverse(child, depth + 1, current_path)

        # 遍历所有根节点
        for root_node in labels:
            traverse(root_node, 0, [])

        # 构建返回结果
        num_levels = len(level_labels)
        level_sizes = [len(level_labels[i]) for i in range(num_levels)]
        max_depth = num_levels

        return {
            'num_levels': num_levels,
            'max_depth': max_depth,
            'level_sizes': level_sizes,
            'level_labels': {k: sorted(list(v)) for k, v in level_labels.items()},
            'parent_to_children': parent_to_children,
            'all_paths': all_paths
        }

    def get_model_config(self) -> Dict[str, Any]:
        """
        获取模型初始化所需的配置

        Returns:
            模型配置字典
        """
        return {
            'num_levels': self.hierarchy_info['num_levels'],
            'level_sizes': self.hierarchy_info['level_sizes'],
            'level_labels': self.hierarchy_info['level_labels']
        }

    def get_hierarchy_info(self) -> Dict[str, Any]:
        """
        获取完整的层级信息

        Returns:
            层级信息字典
        """
        return self.hierarchy_info

    def save_label_mapping(self, output_path: str):
        """
        保存标签映射关系（用于推理时解码）

        Args:
            output_path: 输出文件路径
        """
        mapping = {
            'level_labels': self.hierarchy_info['level_labels'],
            'parent_to_children': self.hierarchy_info['parent_to_children'],
            'all_paths': self.hierarchy_info['all_paths'],
            'config': {
                'num_levels': self.hierarchy_info['num_levels'],
                'max_depth': self.hierarchy_info['max_depth'],
                'level_sizes': self.hierarchy_info['level_sizes']
            }
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        print(f"✅ 标签映射已保存到: {output_path}")

    def print_summary(self):
        """打印配置摘要信息"""
        print("\n" + "="*50)
        print("层级配置摘要")
        print("="*50)
        print(f"版本: {self.config.get('version', 'N/A')}")
        print(f"总层级数: {self.hierarchy_info['num_levels']}")
        print(f"最大深度: {self.hierarchy_info['max_depth']}")
        print(f"\n各层级标签数量:")
        for i, size in enumerate(self.hierarchy_info['level_sizes']):
            print(f"  Level {i}: {size} 个标签")
        print(f"\n各层级标签示例:")
        for i, labels in self.hierarchy_info['level_labels'].items():
            preview = ', '.join(labels[:3])
            more = f" ... 等{len(labels)}个" if len(labels) > 3 else ""
            print(f"  Level {i}: {preview}{more}")
        print(f"\n完整路径数量: {len(self.hierarchy_info['all_paths'])}")
        print("="*50 + "\n")


def create_label_encoders(hierarchy_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    从层级信息创建标签编码器

    Args:
        hierarchy_info: HierarchyConfigParser解析的层级信息

    Returns:
        编码器映射字典，每个层级包含classes和mapping
    """
    encoders = {}

    for level_idx, labels in hierarchy_info['level_labels'].items():
        encoders[f'level{level_idx}'] = {
            'classes': labels,
            'mapping': {label: idx for idx, label in enumerate(labels)}
        }

    return encoders


def main():
    """测试函数"""
    # 示例配置
    example_config = {
        "version": "1.0",
        "labels": [
            {
                "name": "投资理财",
                "children": [
                    {
                        "name": "基金投资",
                        "children": [
                            {"name": "开放式基金", "children": []},
                            {"name": "指数基金", "children": []}
                        ]
                    },
                    {
                        "name": "股票投资",
                        "children": [
                            {
                                "name": "A股交易",
                                "children": [
                                    {"name": "普通交易", "children": []},
                                    {"name": "融资融券", "children": []}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "账户服务",
                "children": [
                    {"name": "开户注销", "children": []}
                ]
            }
        ]
    }

    # 测试解析器
    parser = HierarchyConfigParser(config_dict=example_config)
    parser.print_summary()

    # 获取模型配置
    model_config = parser.get_model_config()
    print("\n模型配置:")
    print(f"  num_levels: {model_config['num_levels']}")
    print(f"  level_sizes: {model_config['level_sizes']}")

    # 保存标签映射
    parser.save_label_mapping("output/test_label_mapping.json")

    # 创建编码器
    encoders = create_label_encoders(parser.get_hierarchy_info())
    print("\n编码器示例:")
    print(f"  Level 0 映射: {encoders['level0']['mapping']}")


if __name__ == "__main__":
    main()
