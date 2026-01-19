import * as fs from 'fs';
import * as path from 'path';

// 三级标签体系定义
interface Label {
  level1: string;
  level2: string;
  level3: string;
}

interface DataItem {
  id: number;
  text: string;
  label_level1: string;
  label_level2: string;
  label_level3: string;
  text_length: string;
  intent_complexity: string;
  sample_type: string;
  keywords: string;
  confidence_score: number;
}

// 完整的标签体系
const labelSystem: Label[] = [
  // 投资理财 - 基金投资
  { level1: '投资理财', level2: '基金投资', level3: '开放式基金' },
  { level1: '投资理财', level2: '基金投资', level3: '指数基金' },
  { level1: '投资理财', level2: '基金投资', level3: '债券基金' },
  { level1: '投资理财', level2: '基金投资', level3: '货币基金' },
  { level1: '投资理财', level2: '基金投资', level3: '基金定投' },
  { level1: '投资理财', level2: '基金投资', level3: '基金转换' },
  { level1: '投资理财', level2: '基金投资', level3: '基金赎回' },

  // 投资理财 - 股票投资
  { level1: '投资理财', level2: '股票投资', level3: 'A股交易' },
  { level1: '投资理财', level2: '股票投资', level3: '港股通' },
  { level1: '投资理财', level2: '股票投资', level3: '美股交易' },
  { level1: '投资理财', level2: '股票投资', level3: '新股申购' },
  { level1: '投资理财', level2: '股票投资', level3: '股票查询' },
  { level1: '投资理财', level2: '股票投资', level3: '持仓分析' },

  // 投资理财 - 理财产品
  { level1: '投资理财', level2: '理财产品', level3: '银行理财' },
  { level1: '投资理财', level2: '理财产品', level3: '净值型理财' },
  { level1: '投资理财', level2: '理财产品', level3: '预期收益型' },
  { level1: '投资理财', level2: '理财产品', level3: '结构性存款' },
  { level1: '投资理财', level2: '理财产品', level3: '大额存单' },

  // 投资理财 - 保险规划
  { level1: '投资理财', level2: '保险规划', level3: '人寿保险' },
  { level1: '投资理财', level2: '保险规划', level3: '健康保险' },
  { level1: '投资理财', level2: '保险规划', level3: '财产保险' },
  { level1: '投资理财', level2: '保险规划', level3: '意外险' },
  { level1: '投资理财', level2: '保险规划', level3: '车险' },
  { level1: '投资理财', level2: '保险规划', level3: '保险理赔' },

  // 投资理财 - 资产配置
  { level1: '投资理财', level2: '资产配置', level3: '资产配置建议' },
  { level1: '投资理财', level2: '资产配置', level3: '风险评估' },
  { level1: '投资理财', level2: '资产配置', level3: '投资组合' },
  { level1: '投资理财', level2: '资产配置', level3: '定期调整' },

  // 信贷服务 - 个人贷款
  { level1: '信贷服务', level2: '个人贷款', level3: '房贷' },
  { level1: '信贷服务', level2: '个人贷款', level3: '消费贷' },
  { level1: '信贷服务', level2: '个人贷款', level3: '经营贷' },
  { level1: '信贷服务', level2: '个人贷款', level3: '信用贷' },
  { level1: '信贷服务', level2: '个人贷款', level3: '抵押贷' },
  { level1: '信贷服务', level2: '个人贷款', level3: '贷款计算' },

  // 信贷服务 - 企业贷款
  { level1: '信贷服务', level2: '企业贷款', level3: '流动资金贷款' },
  { level1: '信贷服务', level2: '企业贷款', level3: '固定资产贷款' },
  { level1: '信贷服务', level2: '企业贷款', level3: '贸易融资' },
  { level1: '信贷服务', level2: '企业贷款', level3: '贷款审批' },

  // 信贷服务 - 信用卡服务
  { level1: '信贷服务', level2: '信用卡服务', level3: '办卡申请' },
  { level1: '信贷服务', level2: '信用卡服务', level3: '信用卡激活' },
  { level1: '信贷服务', level2: '信用卡服务', level3: '额度提升' },
  { level1: '信贷服务', level2: '信用卡服务', level3: '临时额度' },
  { level1: '信贷服务', level2: '信用卡服务', level3: '账单分期' },

  // 信贷服务 - 额度管理
  { level1: '信贷服务', level2: '额度管理', level3: '额度查询' },
  { level1: '信贷服务', level2: '额度管理', level3: '额度调整' },
  { level1: '信贷服务', level2: '额度管理', level3: '授信管理' },
  { level1: '信贷服务', level2: '额度管理', level3: '担保方式' },

  // 账户服务 - 开户注销
  { level1: '账户服务', level2: '开户注销', level3: '个人开户' },
  { level1: '账户服务', level2: '开户注销', level3: '企业开户' },
  { level1: '账户服务', level2: '开户注销', level3: '账户注销' },
  { level1: '账户服务', level2: '开户注销', level3: '休眠账户激活' },

  // 账户服务 - 密码管理
  { level1: '账户服务', level2: '密码管理', level3: '登录密码' },
  { level1: '账户服务', level2: '密码管理', level3: '支付密码' },
  { level1: '账户服务', level2: '密码管理', level3: '密码重置' },
  { level1: '账户服务', level2: '密码管理', level3: '密码找回' },

  // 账户服务 - 权限设置
  { level1: '账户服务', level2: '权限设置', level3: '交易权限' },
  { level1: '账户服务', level2: '权限设置', level3: '转账限额' },
  { level1: '账户服务', level2: '权限设置', level3: '委托授权' },
  { level1: '账户服务', level2: '权限设置', level3: '权限冻结' },

  // 账户服务 - 安全验证
  { level1: '账户服务', level2: '安全验证', level3: '实名认证' },
  { level1: '账户服务', level2: '安全验证', level3: '人脸识别' },
  { level1: '账户服务', level2: '安全验证', level3: '短信验证' },
  { level1: '账户服务', level2: '安全验证', level3: '盾卡管理' },

  // 交易服务 - 转账汇款
  { level1: '交易服务', level2: '转账汇款', level3: '行内转账' },
  { level1: '交易服务', level2: '转账汇款', level3: '跨行转账' },
  { level1: '交易服务', level2: '转账汇款', level3: '实时转账' },
  { level1: '交易服务', level2: '转账汇款', level3: '预约转账' },
  { level1: '交易服务', level2: '转账汇款', level3: '跨境汇款' },

  // 交易服务 - 支付缴费
  { level1: '交易服务', level2: '支付缴费', level3: '水电煤缴费' },
  { level1: '交易服务', level2: '支付缴费', level3: '手机充值' },
  { level1: '交易服务', level2: '支付缴费', level3: '交通罚款' },
  { level1: '交易服务', level2: '支付缴费', level3: '税费缴纳' },

  // 交易服务 - 代扣代缴
  { level1: '交易服务', level2: '代扣代缴', level3: '代扣设置' },
  { level1: '交易服务', level2: '代扣代缴', level3: '代扣取消' },
  { level1: '交易服务', level2: '代扣代缴', level3: '自动缴费' },
  { level1: '交易服务', level2: '代扣代缴', level3: '代扣查询' },

  // 交易服务 - 交易查询
  { level1: '交易服务', level2: '交易查询', level3: '交易明细' },
  { level1: '交易服务', level2: '交易查询', level3: '交易记录' },
  { level1: '交易服务', level2: '交易查询', level3: '电子回单' },
  { level1: '交易服务', level2: '交易查询', level3: '对账单' },

  // 产品咨询 - 产品对比
  { level1: '产品咨询', level2: '产品对比', level3: '收益率对比' },
  { level1: '产品咨询', level2: '产品对比', level3: '风险等级对比' },
  { level1: '产品咨询', level2: '产品对比', level3: '费用对比' },
  { level1: '产品咨询', level2: '产品对比', level3: '产品优缺点' },

  // 产品咨询 - 收益计算
  { level1: '产品咨询', level2: '收益计算', level3: '预期收益' },
  { level1: '产品咨询', level2: '收益计算', level3: '实际收益' },
  { level1: '产品咨询', level2: '收益计算', level3: '复利计算' },
  { level1: '产品咨询', level2: '收益计算', level3: '历史收益查询' },

  // 产品咨询 - 费用说明
  { level1: '产品咨询', level2: '费用说明', level3: '手续费' },
  { level1: '产品咨询', level2: '费用说明', level3: '管理费' },
  { level1: '产品咨询', level2: '费用说明', level3: '赎回费' },
  { level1: '产品咨询', level2: '费用说明', level3: '服务费' },

  // 产品咨询 - 产品推荐
  { level1: '产品咨询', level2: '产品推荐', level3: '稳健型产品' },
  { level1: '产品咨询', level2: '产品推荐', level3: '进取型产品' },
  { level1: '产品咨询', level2: '产品推荐', level3: '低风险产品' },
  { level1: '产品咨询', level2: '产品推荐', level3: '热门产品' },

  // 风险合规 - 风险评估
  { level1: '风险合规', level2: '风险评估', level3: '风险测评' },
  { level1: '风险合规', level2: '风险评估', level3: '风险等级' },
  { level1: '风险合规', level2: '风险评估', level3: '承受能力' },
  { level1: '风险合规', level2: '风险评估', level3: '风险提示' },

  // 风险合规 - 合规咨询
  { level1: '风险合规', level2: '合规咨询', level3: '反洗钱' },
  { level1: '风险合规', level2: '合规咨询', level3: '身份识别' },
  { level1: '风险合规', level2: '合规咨询', level3: '合规要求' },
  { level1: '风险合规', level2: '合规咨询', level3: '监管政策' },

  // 风险合规 - 信息披露
  { level1: '风险合规', level2: '信息披露', level3: '产品公告' },
  { level1: '风险合规', level2: '信息披露', level3: '风险提示书' },
  { level1: '风险合规', level2: '信息披露', level3: '产品说明书' },
  { level1: '风险合规', level2: '信息披露', level3: '信息披露查询' },
];

// 生成样本文本的模板
function generateSamples(label: Label, count: number): DataItem[] {
  const samples: DataItem[] = [];
  const complexities = ['简单', '中等', '复杂'];

  // 定义不同标签的文本模板
  const templates: string[] = getTemplatesForLabel(label);

  for (let i = 0; i < count; i++) {
    const templateIndex = i % templates.length;
    const text = templates[templateIndex];

    // 确定文本长度类型
    let sampleType: string;
    let textLength: string;
    let intentComplexity: string;

    if (text.length <= 30) {
      sampleType = 'short';
      textLength = '短文本';
    } else if (text.length <= 60) {
      sampleType = 'medium';
      textLength = '中等文本';
    } else {
      sampleType = 'long';
      textLength = '长文本';
    }

    // 根据文本长度和复杂度确定意图复杂度
    if (sampleType === 'short') {
      intentComplexity = '简单';
    } else if (sampleType === 'medium') {
      intentComplexity = Math.random() > 0.5 ? '简单' : '中等';
    } else {
      intentComplexity = complexities[Math.floor(Math.random() * complexities.length)];
    }

    // 提取关键词
    const keywords = extractKeywords(text, label);

    samples.push({
      id: samples.length,
      text: text,
      label_level1: label.level1,
      label_level2: label.level2,
      label_level3: label.level3,
      text_length: textLength,
      intent_complexity: intentComplexity,
      sample_type: sampleType,
      keywords: keywords,
      confidence_score: 0.8 + Math.random() * 0.2,
    });
  }

  return samples;
}

function getTemplatesForLabel(label: Label): string[] {
  // 根据不同标签返回不同的文本模板
  const templatesMap: Record<string, string[]> = {
    '开放式基金': [
      '开放式基金怎么买',
      '我想申购开放式基金',
      '开放式基金有哪些',
      '开放式基金的申购流程是什么',
      '开放式基金和封闭式基金有什么区别？我想了解一下它们的主要特点，特别是关于流动性和申购赎回机制方面的差异',
      '请问开放式基金的净值是怎么计算的？我关注的是每日净值更新时间以及计算公式，还有影响净值波动的因素有哪些',
    ],
    '指数基金': [
      '指数基金推荐',
      '什么是指数基金',
      '指数基金怎么选',
      '指数基金跟踪哪些指数',
      '我想投资指数基金，请问沪深300指数基金和上证50指数基金哪个更适合长期持有？',
      '指数基金的费率大概是多少？包括管理费、托管费、申购费和赎回费，还有指数增强型基金和普通指数基金的区别',
    ],
    '债券基金': [
      '债券基金收益怎么样',
      '债券基金风险大吗',
      '纯债基金和混合债基的区别',
      '债券基金适合长期持有吗',
      '我有10万块钱想买债券基金，请问国债基金和信用债基金哪个更安全？收益大概有多少？',
      '债券基金的久期是什么意思？对我选择债券基金有什么影响？请问在利率上行和下行环境下应该怎么选择久期',
    ],
    '基金定投': [
      '基金定投怎么设置',
      '定投基金有什么好处',
      '基金定投多少钱合适',
      '定投基金什么时候止盈',
      '我想做基金定投，每月定投2000元，请问是选周定投好还是月定投好？',
      '基金定投 SMART 定投和普通定投有什么区别？我在什么情况下应该使用智能定投策略？',
    ],
    '房贷': [
      '房贷利率是多少',
      '房贷怎么申请',
      '公积金贷款和商贷的区别',
      '房贷可以提前还款吗',
      '我想买一套房子，贷款200万，30年还清，请问等额本息和等额本金哪种还款方式更划算？',
      '首套房和二套房的房贷利率差多少？我现在有一套房还在贷款中，想再买一套的话首付比例和利率分别是多少',
    ],
    '消费贷': [
      '消费贷利率多少',
      '个人消费贷怎么申请',
      '消费贷能贷多少钱',
      '消费贷需要什么条件',
      '我想装修房子需要30万，请问消费贷的申请流程是什么？需要提供哪些材料？大概多久能批下来',
      '消费贷和信用卡现金分期哪个更划算？我需要借20万用一年，请问哪种方式的利息更低，有没有其他手续费',
    ],
    '信用卡激活': [
      '信用卡怎么激活',
      '收到信用卡后要做什么',
      '信用卡激活期限是多久',
      '信用卡激活要收费吗',
      '我刚收到你们银行寄来的信用卡，请问怎么激活？可以通过手机银行APP操作吗？',
      '我的信用卡寄丢了，请问怎么补办？原信用卡还能继续使用吗？补卡需要多久时间',
    ],
    '额度提升': [
      '怎么提升信用卡额度',
      '信用卡提额需要什么条件',
      '信用卡提额被拒怎么办',
      '临时额度和固定额度的区别',
      '我的信用卡额度是1万，用了半年了，每次都按时还款，请问能提升到多少额度？需要什么条件',
      '申请信用卡提额被拒绝了，请问是是什么原因？我要多久才能再次申请提额',
    ],
    '个人开户': [
      '个人银行账户怎么开',
      '开户需要什么证件',
      '开户要带什么材料',
      '网上银行怎么开户',
      '我想在你们银行开个人账户，请问需要带什么证件？开户需要多长时间？',
      '开户需要本人去银行吗？能不能在手机上直接开户？需要做人脸识别吗',
    ],
    '登录密码': [
      '登录密码忘了怎么办',
      '怎么修改登录密码',
      '登录密码有什么要求',
      '密码输错多次被锁定了',
      '我的网银登录密码忘记了，请问怎么找回？需要去柜台办理吗？',
      '登录密码要求包含大小写字母和数字，请问具体是什么格式？最少要几位字符',
    ],
    '行内转账': [
      '行内转账要手续费吗',
      '行内转账多久到账',
      '怎么行内转账',
      '行内转账限额是多少',
      '我给朋友转钱，他也是你们银行的，请问转账要手续费吗？即时到账吗',
      '行内转账的限额是多少？我需要转账5万块钱，能不能一次性转出去',
    ],
    '跨行转账': [
      '跨行转账多久到账',
      '跨行转账手续费怎么收',
      '跨行转账限额是多少',
      '跨行转账需要什么信息',
      '我需要转账到工商银行，请问多久能到账？手续费怎么计算？',
      '跨行转账需要对方什么信息？只需要银行卡号还是也需要开户行名称？大额转账要提前预约吗',
    ],
    '水电煤缴费': [
      '怎么交水电费',
      '网上银行能缴水电费吗',
      '水电煤缴费要手续费吗',
      '怎么设置自动缴费',
      '我想用手机银行交家里的水电费和燃气费，请问怎么操作？需要绑定户号吗',
      '请问能不能设置自动扣款缴费？每月自动从我的账户里扣水电费，怎么开通这个功能',
    ],
    '手机充值': [
      '手机话费怎么充值',
      '手机银行能充值吗',
      '充值话费有优惠吗',
      '充值没到账怎么办',
      '手机银行可以给手机充值吗？我有两张手机卡都能充吗？',
      '话费充值到账时间是多久？刚充了话费还没到账，请问要等多久',
    ],
    '产品对比': [
      '这两款理财产品哪个好',
      '理财产品怎么选',
      '净值型理财和预期收益型哪个好',
      '不同风险等级的理财产品区别',
      '我有两款理财产品A和B，A的预期收益率是4.5%，B是4.2%，但A是R3风险等级，B是R2，请问哪个更适合我',
      '理财产品的风险等级是怎么划分的？R1到R5分别代表什么风险级别？我风险承受能力中等，应该选哪个等级的产品',
    ],
    '收益计算': [
      '理财收益怎么算',
      '5万元买理财一年能赚多少',
      '理财产品收益怎么查询',
      '实际收益和预期收益的区别',
      '我有10万块钱，买年化收益率4%的理财产品，一年能拿到多少利息？是按月付息还是到期一次性还本付息',
      '理财产品的七日年化和年化收益率有什么区别？我看到的收益率是哪个数据，怎么计算我能拿到多少钱',
    ],
    '风险评估': [
      '风险评估怎么做',
      '风险评估有效期多久',
      '风险评估不通过怎么办',
      '风险测评是什么',
      '我要买理财产品，系统提示我要做风险评估，请问这个测评在哪里做？需要多长时间',
      '我的风险评估结果是稳健型，请问可以买哪些理财产品？能不能买R3风险等级的产品',
    ],
    '反洗钱': [
      '什么是反洗钱',
      '反洗钱要提供什么材料',
      '大额交易需要申报吗',
      '反洗钱审核要多久',
      '我有一笔10万的大额转账，为什么会要求我提供资金来源和用途证明',
      '开户时要做反洗钱身份识别，请问需要提供什么信息？为什么还要问我的职业和年收入',
    ],
  };

  // 如果没有特定模板，返回通用模板
  const defaultTemplates = [
    `请问${label.level3}怎么操作`,
    `我想了解${label.level3}的相关信息`,
    `${label.level3}的具体流程是什么`,
    `${label.level3}需要什么条件`,
    `我对${label.level3}很感兴趣，请问能介绍一下吗？我想知道相关的具体要求和办理流程`,
    `请问${label.level3}和其他类似服务相比有什么优势？我想做一个详细的了解和对比，看看哪个更适合我的需求`,
  ];

  return templatesMap[label.level3] || defaultTemplates;
}

function extractKeywords(text: string, label: Label): string {
  // 简单的关键词提取逻辑
  const keywords: string[] = [];

  // 从三级标签中提取关键词
  keywords.push(label.level3);

  // 从文本中提取常见金融关键词
  const financialKeywords = [
    '利率', '费率', '收益', '风险', '额度', '贷款', '存款', '基金',
    '股票', '理财', '保险', '信用卡', '转账', '缴费', '开户',
    '密码', '申请', '查询', '办理', '流程', '条件', '材料', '手续费',
  ];

  financialKeywords.forEach(keyword => {
    if (text.includes(keyword) && !keywords.includes(keyword)) {
      keywords.push(keyword);
    }
  });

  // 最多返回5个关键词
  return keywords.slice(0, 5).join(', ');
}

// 生成完整数据集
function generateDataset(totalSamples: number = 2000): DataItem[] {
  const dataset: DataItem[] = [];
  const labelsPerSample = Math.floor(totalSamples / labelSystem.length);
  const remainder = totalSamples % labelSystem.length;

  labelSystem.forEach((label, index) => {
    const count = index < remainder ? labelsPerSample + 1 : labelsPerSample;
    const samples = generateSamples(label, count);
    dataset.push(...samples);
  });

  // 打乱数据集
  for (let i = dataset.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [dataset[i], dataset[j]] = [dataset[j], dataset[i]];
  }

  // 重新分配ID
  dataset.forEach((item, index) => {
    item.id = index;
  });

  return dataset;
}

// 转换为CSV格式
function toCSV(dataset: DataItem[]): string {
  const headers = ['id', 'text', 'label_level1', 'label_level2', 'label_level3',
                   'text_length', 'intent_complexity', 'sample_type', 'keywords', 'confidence_score'];

  const rows = dataset.map(item =>
    `${item.id},"${item.text.replace(/"/g, '""')}","${item.label_level1}","${item.label_level2}","${item.label_level3}","${item.text_length}","${item.intent_complexity}","${item.sample_type}","${item.keywords}",${item.confidence_score.toFixed(2)}`
  );

  return [headers.join(','), ...rows].join('\n');
}

// 生成验证集
function generateValidationSet(validationSize: number = 300): DataItem[] {
  console.log('\n========================================');
  console.log('开始生成验证集...');

  const validationSet = generateDataset(validationSize);

  // 统计信息
  const level1Count = new Map<string, number>();
  validationSet.forEach(item => {
    level1Count.set(item.label_level1, (level1Count.get(item.label_level1) || 0) + 1);
  });

  console.log(`\n验证集生成完成！`);
  console.log(`验证集数据量: ${validationSet.length}条`);

  console.log('\n验证集一级标签分布:');
  level1Count.forEach((count, label) => {
    console.log(`  ${label}: ${count}条 (${(count / validationSet.length * 100).toFixed(1)}%)`);
  });

  // 文本长度分布
  const lengthCount = new Map<string, number>();
  validationSet.forEach(item => {
    lengthCount.set(item.text_length, (lengthCount.get(item.text_length) || 0) + 1);
  });

  console.log('\n验证集文本长度分布:');
  lengthCount.forEach((count, type) => {
    console.log(`  ${type}: ${count}条 (${(count / validationSet.length * 100).toFixed(1)}%)`);
  });

  return validationSet;
}

// 主函数
function main() {
  console.log('开始生成金融领域BERT分类数据集...');
  console.log(`目标数据量: 2000条`);
  console.log(`一级标签数量: 6个`);
  console.log(`二级标签数量: 24个`);
  console.log(`三级标签数量: 108个`);

  const dataset = generateDataset(2000);

  console.log(`\n实际生成数据量: ${dataset.length}条`);

  // 统计信息
  const level1Count = new Map<string, number>();
  const level2Count = new Map<string, number>();
  const level3Count = new Map<string, number>();

  dataset.forEach(item => {
    level1Count.set(item.label_level1, (level1Count.get(item.label_level1) || 0) + 1);
    level2Count.set(item.label_level2, (level2Count.get(item.label_level2) || 0) + 1);
    level3Count.set(item.label_level3, (level3Count.get(item.label_level3) || 0) + 1);
  });

  console.log('\n一级标签分布:');
  level1Count.forEach((count, label) => {
    console.log(`  ${label}: ${count}条`);
  });

  // 文本长度分布
  const lengthCount = new Map<string, number>();
  dataset.forEach(item => {
    lengthCount.set(item.text_length, (lengthCount.get(item.text_length) || 0) + 1);
  });

  console.log('\n文本长度分布:');
  lengthCount.forEach((count, type) => {
    console.log(`  ${type}: ${count}条 (${(count / dataset.length * 100).toFixed(1)}%)`);
  });

  // 保存CSV文件
  const csv = toCSV(dataset);
  const outputPath = path.join(__dirname, '..', 'financial_intent_dataset.csv');
  fs.writeFileSync(outputPath, '\uFEFF' + csv, 'utf-8'); // 添加BOM确保Excel正确识别中文

  console.log(`\n数据集已保存到: ${outputPath}`);
  console.log(`文件大小: ${(csv.length / 1024).toFixed(2)} KB`);

  // 保存标签体系说明
  const labelInfo: any = {
    total_labels: labelSystem.length,
    level1_categories: [...new Set(labelSystem.map(l => l.level1))],
    level2_categories: [...new Set(labelSystem.map(l => l.level2))],
    level3_categories: [...new Set(labelSystem.map(l => l.level3))],
    full_hierarchy: labelSystem
  };

  const infoPath = path.join(__dirname, '..', 'dataset_labels_info.json');
  fs.writeFileSync(infoPath, JSON.stringify(labelInfo, null, 2), 'utf-8');

  console.log(`标签体系说明已保存到: ${infoPath}`);

  // 生成验证集
  const validationSet = generateValidationSet(300);

  // 保存验证集CSV文件
  const validationCSV = toCSV(validationSet);
  const validationPath = path.join(__dirname, '..', 'financial_intent_validation.csv');
  fs.writeFileSync(validationPath, '\uFEFF' + validationCSV, 'utf-8');

  console.log(`\n验证集已保存到: ${validationPath}`);
  console.log(`文件大小: ${(validationCSV.length / 1024).toFixed(2)} KB`);

  // 更新标签体系说明，包含数据集信息
  labelInfo.dataset_info = {
    training_set: {
      file: 'financial_intent_dataset.csv',
      size: dataset.length,
      path: outputPath
    },
    validation_set: {
      file: 'financial_intent_validation.csv',
      size: validationSet.length,
      path: validationPath
    },
    total_size: dataset.length + validationSet.length
  };

  fs.writeFileSync(infoPath, JSON.stringify(labelInfo, null, 2), 'utf-8');

  console.log(`\n========================================`);
  console.log('所有数据集生成完成！');
  console.log(`- 训练集: ${dataset.length}条`);
  console.log(`- 验证集: ${validationSet.length}条`);
  console.log(`- 总计: ${dataset.length + validationSet.length}条`);
  console.log('========================================');
}

main();
