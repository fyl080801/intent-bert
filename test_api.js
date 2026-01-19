/**
 * API测试脚本 - 测试BERT金融意图分类模型
 */

const axios = require('axios');
const API_BASE = 'http://localhost:3000';

// 测试语料 - 覆盖不同金融领域意图
const testCorpus = [
  // 投资理财 - 基金投资
  {
    text: "我想买一些基金，有什么推荐的吗？",
    expected: {
      level1: "投资理财",
      level2: "基金投资",
      level3: "开放式基金"
    },
    category: "基金推荐"
  },
  {
    text: "怎么开通基金定投？",
    expected: {
      level1: "投资理财",
      level2: "基金投资",
      level3: "基金定投"
    },
    category: "基金定投"
  },
  {
    text: "我要赎回我的货币基金",
    expected: {
      level1: "投资理财",
      level2: "基金投资",
      level3: "基金赎回"
    },
    category: "基金赎回"
  },

  // 投资理财 - 股票投资
  {
    text: "今天A股大盘怎么样？",
    expected: {
      level1: "投资理财",
      level2: "股票投资",
      level3: "A股交易"
    },
    category: "A股查询"
  },
  {
    text: "我想申购新股，需要满足什么条件？",
    expected: {
      level1: "投资理财",
      level2: "股票投资",
      level3: "新股申购"
    },
    category: "新股申购"
  },
  {
    text: "如何通过港股通买入港股？",
    expected: {
      level1: "投资理财",
      level2: "股票投资",
      level3: "港股通"
    },
    category: "港股通"
  },

  // 信贷服务 - 个人贷款
  {
    text: "我想申请房屋贷款，利率是多少？",
    expected: {
      level1: "信贷服务",
      level2: "个人贷款",
      level3: "房贷"
    },
    category: "房贷咨询"
  },
  {
    text: "消费贷款的额度最高可以贷多少？",
    expected: {
      level1: "信贷服务",
      level2: "个人贷款",
      level3: "消费贷"
    },
    category: "消费贷"
  },

  // 信贷服务 - 信用卡服务
  {
    text: "怎么办理信用卡？",
    expected: {
      level1: "信贷服务",
      level2: "信用卡服务",
      level3: "办卡申请"
    },
    category: "办卡申请"
  },
  {
    text: "我的信用卡账单想分期还款",
    expected: {
      level1: "信贷服务",
      level2: "信用卡服务",
      level3: "账单分期"
    },
    category: "账单分期"
  },

  // 账户服务 - 开户注销
  {
    text: "我要开一个个人银行账户",
    expected: {
      level1: "账户服务",
      level2: "开户注销",
      level3: "个人开户"
    },
    category: "个人开户"
  },
  {
    text: "企业开户需要准备什么材料？",
    expected: {
      level1: "账户服务",
      level2: "开户注销",
      level3: "企业开户"
    },
    category: "企业开户"
  },

  // 账户服务 - 密码管理
  {
    text: "我忘记登录密码了怎么办？",
    expected: {
      level1: "账户服务",
      level2: "密码管理",
      level3: "密码找回"
    },
    category: "密码找回"
  },
  {
    text: "怎么重置支付密码？",
    expected: {
      level1: "账户服务",
      level2: "密码管理",
      level3: "密码重置"
    },
    category: "密码重置"
  },

  // 交易服务 - 转账汇款
  {
    text: "我要转账到工商银行",
    expected: {
      level1: "交易服务",
      level2: "转账汇款",
      level3: "跨行转账"
    },
    category: "跨行转账"
  },
  {
    text: "能不能设置一个定时转账？",
    expected: {
      level1: "交易服务",
      level2: "转账汇款",
      level3: "预约转账"
    },
    category: "预约转账"
  },

  // 交易服务 - 支付缴费
  {
    text: "我要交水电费",
    expected: {
      level1: "交易服务",
      level2: "支付缴费",
      level3: "水电煤缴费"
    },
    category: "生活缴费"
  },
  {
    text: "手机话费充值",
    expected: {
      level1: "交易服务",
      level2: "支付缴费",
      level3: "手机充值"
    },
    category: "手机充值"
  },

  // 产品咨询 - 收益计算
  {
    text: "帮我算一下理财产品的预期收益",
    expected: {
      level1: "产品咨询",
      level2: "收益计算",
      level3: "预期收益"
    },
    category: "收益计算"
  },
  {
    text: "这个基金的历史收益怎么样？",
    expected: {
      level1: "产品咨询",
      level2: "收益计算",
      level3: "历史收益查询"
    },
    category: "历史收益"
  },

  // 风险合规 - 风险评估
  {
    text: "我要做风险测评",
    expected: {
      level1: "风险合规",
      level2: "风险评估",
      level3: "风险测评"
    },
    category: "风险测评"
  },
  {
    text: "我的风险承受能力是哪个等级？",
    expected: {
      level1: "风险合规",
      level2: "风险评估",
      level3: "承受能力"
    },
    category: "风险等级"
  }
];

/**
 * 测试单条预测
 */
async function testPrediction(testItem) {
  try {
    const response = await axios.post(`${API_BASE}/api/predict`, {
      text: testItem.text
    });

    const result = response.data.data;
    const match = {
      level1: result.label_level1 === testItem.expected.level1,
      level2: result.label_level2 === testItem.expected.level2,
      level3: result.label_level3 === testItem.expected.level3
    };

    return {
      text: testItem.text,
      category: testItem.category,
      predicted: {
        level1: result.label_level1,
        level2: result.label_level2,
        level3: result.label_level3
      },
      expected: testItem.expected,
      confidence: result.overall_confidence,
      match: match,
      allMatch: match.level1 && match.level2 && match.level3
    };
  } catch (error) {
    return {
      text: testItem.text,
      category: testItem.category,
      error: error.message,
      allMatch: false
    };
  }
}

/**
 * 运行批量测试
 */
async function runBatchTest() {
  console.log('='.repeat(80));
  console.log('BERT金融意图分类模型 - API测试');
  console.log('='.repeat(80));
  console.log(`测试样本数: ${testCorpus.length}`);
  console.log('');

  const results = [];

  for (let i = 0; i < testCorpus.length; i++) {
    const testItem = testCorpus[i];
    console.log(`[${i + 1}/${testCorpus.length}] 测试: ${testItem.category}`);
    const result = await testPrediction(testItem);
    results.push(result);
  }

  // 统计结果
  const totalTests = results.length;
  const correctLevel1 = results.filter(r => r.match && r.match.level1).length;
  const correctLevel2 = results.filter(r => r.match && r.match.level2).length;
  const correctLevel3 = results.filter(r => r.match && r.match.level3).length;
  const allCorrect = results.filter(r => r.allMatch).length;

  console.log('\n' + '='.repeat(80));
  console.log('测试结果汇总');
  console.log('='.repeat(80));
  console.log(`总样本数: ${totalTests}`);
  console.log(`一级标签准确率: ${(correctLevel1 / totalTests * 100).toFixed(2)}% (${correctLevel1}/${totalTests})`);
  console.log(`二级标签准确率: ${(correctLevel2 / totalTests * 100).toFixed(2)}% (${correctLevel2}/${totalTests})`);
  console.log(`三级标签准确率: ${(correctLevel3 / totalTests * 100).toFixed(2)}% (${correctLevel3}/${totalTests})`);
  console.log(`完全匹配率: ${(allCorrect / totalTests * 100).toFixed(2)}% (${allCorrect}/${totalTests})`);

  // 显示错误案例
  const errors = results.filter(r => !r.allMatch && !r.error);
  if (errors.length > 0) {
    console.log('\n' + '='.repeat(80));
    console.log('错误案例分析');
    console.log('='.repeat(80));
    errors.forEach((error, index) => {
      console.log(`\n[错误 ${index + 1}] ${error.category}`);
      console.log(`  输入: ${error.text}`);
      console.log(`  预测: L1=${error.predicted.level1}, L2=${error.predicted.level2}, L3=${error.predicted.level3}`);
      console.log(`  期望: L1=${error.expected.level1}, L2=${error.expected.level2}, L3=${error.expected.level3}`);
      console.log(`  置信度: ${error.confidence}`);
    });
  }

  // 显示所有结果详情
  console.log('\n' + '='.repeat(80));
  console.log('详细测试结果');
  console.log('='.repeat(80));
  results.forEach((result, index) => {
    const status = result.allMatch ? '✓' : '✗';
    console.log(`\n${status} [${index + 1}] ${result.category}`);
    console.log(`  输入: ${result.text}`);
    if (result.error) {
      console.log(`  错误: ${result.error}`);
    } else {
      console.log(`  预测: L1=${result.predicted.level1} | L2=${result.predicted.level2} | L3=${result.predicted.level3}`);
      console.log(`  期望: L1=${result.expected.level1} | L2=${result.expected.level2} | L3=${result.expected.level3}`);
      console.log(`  置信度: ${result.confidence}`);
    }
  });

  console.log('\n' + '='.repeat(80));
  console.log('测试完成!');
  console.log('='.repeat(80));
}

// 运行测试
runBatchTest().catch(error => {
  console.error('测试失败:', error.message);
  process.exit(1);
});
