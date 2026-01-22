#!/usr/bin/env python3
"""
K8s BERT 推理服务测试客户端
"""

import requests
import json

# 推理服务端点（通过 NodePort 访问）
INFERENCE_URL = "http://192.168.68.110:30500/predict"

def test_inference(text: str):
    """测试推理服务"""
    print(f"\n{'='*60}")
    print(f"测试文本: {text}")
    print(f"{'='*60}")

    try:
        response = requests.post(
            INFERENCE_URL,
            json={"text": text},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 推理成功:")
            print(f"  一级标签: {result['label_level1']} (置信度: {result['confidence_level1']:.2%})")
            print(f"  二级标签: {result['label_level2']} (置信度: {result['confidence_level2']:.2%})")
            print(f"  三级标签: {result['label_level3']} (置信度: {result['confidence_level3']:.2%})")
            print(f"  综合置信度: {result['overall_confidence']:.2%}")
            return result
        else:
            print(f"\n❌ 请求失败: HTTP {response.status_code}")
            print(response.text)
            return None

    except requests.exceptions.Timeout:
        print(f"\n❌ 请求超时")
        return None
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return None

def main():
    """主测试函数"""
    print("\n🚀 K8s BERT 推理服务测试")
    print(f"服务地址: {INFERENCE_URL}")

    # 测试用例
    test_cases = [
        "我想查询我的银行卡余额",
        "信用卡额度怎么提升",
        "我要申请个人贷款",
        "转账给朋友",
        "理财产品收益怎么样",
        "账户被冻结了怎么办",
        "开通网上银行",
        "挂失银行卡"
    ]

    results = []
    for text in test_cases:
        result = test_inference(text)
        results.append(result)

    # 统计
    print(f"\n{'='*60}")
    print("📊 测试统计")
    print(f"{'='*60}")
    success_count = sum(1 for r in results if r is not None)
    print(f"总测试数: {len(test_cases)}")
    print(f"成功数: {success_count}")
    print(f"失败数: {len(test_cases) - success_count}")
    print(f"成功率: {success_count/len(test_cases):.1%}")

if __name__ == "__main__":
    main()
