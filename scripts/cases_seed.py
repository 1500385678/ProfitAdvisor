#!/usr/bin/env python3
"""
cases_seed.py · Phase 0 #4
==========================
把首批 13 个盈利/定价案例入库到 content/cases/,作为 Phase 1 /case API 的种子数据。

输入: 内置 13 个 CaseSpec(覆盖主计划 4.2 五大类:定价/增长/转型/失败/中国)
输出:
  - content/cases/<id>.json   单个案例定义
  - content/cases/_index.json 聚合索引(分类/数量/标签)

设计原则 (Phase 0 阶段):
  - 0 外部依赖,只 stdlib,与 calculators_seed.py 风格保持一致
  - 每个案例 id 稳定 slug,便于 Phase 1 /case/<id> 接口直接引用
  - 字段留 extension_points(knowledge_ids[]/calculators[]/lessons[]),Phase 1 可直接灌库
  - 数据/数字字段以 JSON 结构存储(主计划 4.3 profit_cases.data JSONB 形态)

扩展点 (留给后续 Phase):
  - Phase 1:接入 FastAPI /case/<id>/read + 关键词检索
  - Phase 2:补全 knowledge_ids/calculators 关联(从已入库的 content/knowledge + content/calculators 抽)
  - Phase 3:由 LLM 自动生成 lessons[] / explanation[] 三件套讲解

Usage:
  python3 scripts/cases_seed.py --out content/cases
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


# ---------- 数据模型 ----------
@dataclass
class CaseSpec:
    """单个案例定义(主计划 4.3 profit_cases 表的 JSON 形态)"""
    id: str
    title: str
    company: str
    industry: str
    topic: str                    # 定价/增长/转型/失败/中国
    region: str = "全球"          # 中国/美国/欧洲/全球
    period: str = ""              # 案例发生的时间段(例: "2017-2019")
    background: str = ""          # 背景描述
    data: dict = field(default_factory=dict)          # 关键数字 {revenue, growth, margin, ...}
    decisions: list[str] = field(default_factory=list)  # 关键决策点
    reflection: str = ""          # 反思/教训
    lessons: list[str] = field(default_factory=list)  # 可迁移的要点
    tags: list[str] = field(default_factory=list)
    knowledge_ids: list[str] = field(default_factory=list)  # 关联知识点
    calculators: list[str] = field(default_factory=list)    # 关联计算器 id
    sources: list[str] = field(default_factory=list)        # 数据来源/参考


# ---------- 13 个种子案例(覆盖五大类) ----------
SEED_CASES: list[CaseSpec] = [
    # ===== 定价类(5) =====
    CaseSpec(
        id="coca_cola_anchor_pricing",
        title="可口可乐的锚定定价:让 99¢ 成为美国便利店标准",
        company="可口可乐",
        industry="饮料",
        topic="定价",
        region="美国",
        period="1886-至今",
        background="可口可乐在 1886 年上市时定价 5 美分/瓶,在 1919 年上市前保持 5¢ 不变近 40 年。"
                   "5¢ 成为消费者心理锚点,后续 1955 年推 7oz 瓶仍用 5¢ 营销(瓶身容量缩水),"
                   "直到 1959 年才调价到 6¢,此后即便通胀调价,99¢ / $1.99 / $2.99 仍是常见锚点。",
        data={
            "original_price_1886": 0.05,           # USD/瓶
            "price_1955_7oz": 0.05,                # 仍 5 美分但容量降到 7oz
            "revenue_2023_billion_usd": 45.75,     # 2023 年营收
            "operating_margin_2023": 0.243,
        },
        decisions=[
            "近 40 年不调价,把 5¢ 钉入消费者心理",
            "调价时改用容量(7oz / 10oz / 12oz)而非涨价,降低感知成本",
            "零售价长期用 99¢ / $1.99 / $2.99 锚点,触发'低于 1 美元'心理账户",
        ],
        reflection="锚定定价的本质不是'价格低',而是'价格稳定 + 数字友好'。"
                   "可口可乐 40 年不调价建立了'日常品'心智,后续即便涨价消费者也归因于容量而非品牌贪婪。",
        lessons=[
            "心理价位(9 结尾)比绝对低价更能拉新客",
            "调价优先改容量,再改价格,降低反弹",
            "价格锚点要长期一致,不要为了促销频繁打破",
        ],
        tags=["锚定定价", "心理定价", "9 结尾", "品牌心智"],
        knowledge_ids=["pricing_strategy__锚定定价", "pricing_strategy__心理定价"],
        calculators=["cost_plus_pricing", "value_based_pricing"],
        sources=["可口可乐官方年报 2023", "The Story of Coca-Cola (Mark Pendergrast)"],
    ),
    CaseSpec(
        id="apple_iphone_value_pricing",
        title="苹果 iPhone 的价值定价:从 $499 入门到 $1599 Pro Max 的价格阶梯",
        company="Apple",
        industry="消费电子",
        topic="定价",
        region="美国",
        period="2007-至今",
        background="2007 年初代 iPhone $499(4GB)/ $599(8GB),后续靠存储/屏幕/材质/Pro/Plus 拉出 $799→$1599 共 6 档。"
                   "2023 财年 iPhone 营收约 $200B,占苹果总营收 52%,ASP(平均售价)稳定在 $900+。",
        data={
            "iphone_revenue_2023_billion_usd": 200.0,
            "asp_2023_usd": 900,
            "gross_margin_iphone": 0.38,
            "product_tiers": 6,                    # SE / 标准 / Plus / Pro / Pro Max / 折叠(传闻)
        },
        decisions=[
            "价值定价而非成本加成:锚点在'我能给客户创造什么'而非 BOM",
            "Pro/Pro Max 与标准版拉出 $400 价差,引导高利润用户上探",
            "存储从 64GB 升 256GB 加 $100,而非按成本,$/GB 阶梯式涨价",
        ],
        reflection="价值定价的关键是'阶梯化'。一个 SKU 只能赚一道钱,6 个 SKU 赚 6 道钱,且高端拉利润、低端拉用户基数。",
        lessons=[
            "至少 3 档 SKU,中间档是利润锚(避免中端被低估)",
            "存储/颜色/材质是天然的阶梯化维度,几乎零 BOM 成本",
            "不要轻易降价:苹果从不在新机发布后 12 个月内官方降价",
        ],
        tags=["价值定价", "阶梯定价", "消费电子", "品牌溢价"],
        knowledge_ids=["pricing_strategy__价值定价", "pricing_strategy__阶梯定价"],
        calculators=["value_based_pricing", "contribution_margin"],
        sources=["Apple 10-K 2023", "TechInsights iPhone BOM 分析"],
    ),
    CaseSpec(
        id="netflix_subscription_tiers",
        title="Netflix 订阅阶梯:从 $7.99 单档到 4 档含广告版,2022 流失逆转",
        company="Netflix",
        industry="流媒体",
        topic="定价",
        region="美国",
        period="2007-2024",
        background="2014 年起 Netflix 把 DVD + 流媒体分离定价,2020 年取消免费试用,"
                   "2022 年 Q1 流失 20 万订阅(十年首次),随即推 Basic($6.99) / Standard 含广告($6.99)/ Standard($15.49)/ Premium($22.99) 四档 + 打击共享密码,"
                   "2023 Q3 净增 876 万订阅,2024 年含广告版突破 7000 万全球用户。",
        data={
            "subscribers_2024_million": 282.7,
            "ad_tier_subscribers_2024_q4_million": 70,
            "tiers_count": 4,
            "price_range_usd": "6.99 - 22.99",
            "q1_2022_churn_k": -200,                 # 流失
            "q3_2023_net_adds_million": 8.76,
        },
        decisions=[
            "广告版 $6.99 拉新,Premium $22.99 拉利润,中段 $15.49 是利润锚",
            "把共享密码'灰色行为'正式商业化(Extra Member 插槽)",
            "广告库存卖给 Microsoft,让 MS 承担广告技术栈,Netflix 抽成",
        ],
        reflection="订阅产品的定价难在'老用户'。Netflix 2022 危机证明,涨价 + 共享打击一次性伤害,"
                   "但通过广告版回填低价用户,把流失变成新档位,完成 ARPU 结构的健康化。",
        lessons=[
            "订阅产品一定要 ≥ 3 档,中段是利润锚",
            "涨价 + 推低价版 + 严打共享 三件套可同时做,不必等数据先动",
            "广告版不能'廉价感',要做出独立价值(新内容/独家剧)",
        ],
        tags=["订阅", "阶梯定价", "广告", "用户分层"],
        knowledge_ids=["pricing_strategy__订阅定价", "pricing_strategy__价值定价"],
        calculators=["ltv_cac", "payback_period"],
        sources=["Netflix 2023 / 2024 季报", "Antenna 订阅经济报告"],
    ),
    CaseSpec(
        id="lucky_coffee_discount_bombing",
        title="瑞幸咖啡:用 1.8 折券烧出 2 万家门店,2023 年首次盈利",
        company="瑞幸咖啡",
        industry="餐饮零售",
        topic="定价",
        region="中国",
        period="2017-2024",
        background="2017 年开出第一家店,2018-2019 用 1.8 折券 + 首杯免费快速拉新,"
                   "2019 年纳斯达克上市,2020 年因 22 亿财务造假被退市,2021-2022 关店瘦身,"
                   "2023 年门店破 2 万超越星巴克中国,2023 Q3 净利润 9.9 亿,首次单季盈利。",
        data={
            "stores_2023": 20000,                    # 2 万家
            "stores_2019_peak": 4500,               # 高峰期
            "first_profit_quarter": "2023 Q3",
            "q3_2023_net_profit_million_cny": 990,
            "discount_rate_2019": 0.18,              # 1.8 折券
            "asp_cny_2019": 9.0,                     # 券后价
        },
        decisions=[
            "用 1.8 折券把咖啡单价从 30+ 砸到 9 元,重塑'日常咖啡'心智",
            "小程序 + 自提模型砍掉堂食成本,单店模型跑通",
            "造假退市后砍掉价格战 + 严选合伙人,走加盟模型",
        ],
        reflection="瑞幸证明了'补贴 + 密度'可以烧出垄断心智,但财务造假让它付出退市代价;"
                   "回血关键不是停止补贴,而是把单店模型跑通(自提 + 小程序)再恢复价格。",
        lessons=[
            "现金补贴必须服务于'单店模型跑通',否则是纯烧钱",
            "密度优先于盈利:2 万家门店的供应链议价权是后来盈利的根",
            "财务造假不可逆,补贴节奏比补贴幅度更关键",
        ],
        tags=["补贴", "密度", "小程序", "单店模型"],
        knowledge_ids=["pricing_strategy__渗透定价", "unit_economics__LTV"],
        calculators=["ltv_cac", "payback_period", "break_even_point"],
        sources=["瑞幸 2023 Q3 财报", "晚点 LatePost 深度报道"],
    ),
    CaseSpec(
        id="costco_membership_anchor",
        title="Costco 会员费:商品亏本卖,一年收 $58 亿会员费才是利润",
        company="Costco",
        industry="零售",
        topic="定价",
        region="美国",
        period="1983-至今",
        background="Costco 全球门店商品平均毛利率仅 11%(普通超市 25-35%),"
                   "利润几乎全部来自会员费,2023 财年会员费收入 $45.8 亿 / 净利润 $62.9 亿,会员费占净利 73%。"
                   "黑卡($120/年)续卡率 92.5%,远超行业 60%。",
        data={
            "merchandise_margin": 0.11,              # 商品毛利
            "membership_fee_revenue_2023_billion_usd": 4.58,
            "net_profit_2023_billion_usd": 6.29,
            "membership_profit_share": 0.73,
            "executive_renewal_rate": 0.925,
            "executive_fee_usd": 120,
        },
        decisions=[
            "商品定价'不超 14% 加成',书面写入员工守则",
            "会员费上调极慢(2017 金卡 $55→$60,2020 黑卡 $110→$120),用'不涨价'换续卡率",
            "自有品牌 Kirkland 撑起高 ASP,会员感知'省更多'",
        ],
        reflection="Costco 的本质是'会员费订阅制零售'。商品亏本卖换心智,会员费才是真利润。"
                   "这是订阅经济的零售变体,订阅产品的核心 KPI 是续费率,不是 GMV。",
        lessons=[
            "低价不是策略,低价 + 锁定复购才是",
            "会员费涨价节奏要远低于通胀,稳定预期换续卡率",
            "毛利率封顶写入制度,避免管理层短期逐利",
        ],
        tags=["会员制", "订阅", "毛利率封顶", "续卡率"],
        knowledge_ids=["pricing_strategy__会员制", "unit_economics__续费率"],
        calculators=["ltv_cac", "payback_period"],
        sources=["Costco 2023 10-K", "NYT 'How Costco Wins'"],
    ),
    # ===== 增长类(2) =====
    CaseSpec(
        id="saas_unit_economics_growth",
        title="SaaS 单位经济:从 LTV/CAC 1.5 到 5.0 的 Slack 增长模型",
        company="Slack",
        industry="SaaS",
        topic="增长",
        region="美国",
        period="2013-2019",
        background="Slack 2013 年公开测试,2014 年估值 $250M,2019 年纽交所直接上市(DPO)估值 $197 亿。"
                   "早期靠'底部免费 + 病毒传播'(团队内一人用 → 全公司用)实现 LTV/CAC > 3,"
                   "但 CAC 持续上涨(2017 $1 → 2019 $1.5)最终拖到上市前都未盈利,2021 年被 Salesforce $277 亿收购。",
        data={
            "ltv_cac_2014": 5.0,                    # 早期
            "ltv_cac_2018": 1.5,                    # 后期
            "cac_2017_usd": 1.0,                    # 自然获客
            "cac_2019_usd": 1.5,
            "2019_revenue_million_usd": 630,
            "valuation_ipo_billion_usd": 19.7,
        },
        decisions=[
            "底部免费 + 单团队病毒传播(团队每多 1 人,获客成本边际 = 0)",
            "把 NPS 做为核心指标,> 50 视为 PMF 成立",
            "后期投付费广告拉新客,稀释了 LTV/CAC",
        ],
        reflection="Slack 早期是教科书级'病毒 SaaS'案例,但增长后期陷入'自然增长见顶 + 付费拉新抬 CAC'两难。"
                   "LTV/CAC 从 5 跌到 1.5 提醒:PLG 产品的护城河是产品本身的传播力,不是广告。",
        lessons=[
            "LTV/CAC 早期 5+ 不可持续,3 是健康线",
            "PLG 的天花板是产品 NPS,不是市场预算",
            "DPO 是 SaaS 终局(被收购)的预演,IPO 反而难",
        ],
        tags=["SaaS", "PLG", "病毒传播", "LTV/CAC"],
        knowledge_ids=["unit_economics__LTV", "unit_economics__CAC"],
        calculators=["ltv_cac", "payback_period", "growth_funnel_conversion"],
        sources=["Slack S-1 2019", "Bessemer State of the Cloud"],
    ),
    CaseSpec(
        id="lucky_coffee_density_play",
        title="瑞幸 2 万店:用'密度 + 自提'打破星巴克的'第三空间'神话",
        company="瑞幸咖啡",
        industry="餐饮零售",
        topic="增长",
        region="中国",
        period="2017-2023",
        background="星巴克 1999 入华,25 年开 6500 家;瑞幸 2017-2023 6 年开 2 万家。"
                   "关键:砍掉堂食(80% 店是 Pickup,面积 20-60㎡) + 小程序点单 + 9 元券后均价,做到'30 米必有瑞幸'。",
        data={
            "lucky_stores_2023": 20000,
            "starbucks_china_stores_2023": 6500,
            "pickup_store_ratio": 0.8,
            "ticket_size_cny": 15,                  # 券后
            "year_to_20k": 6,
        },
        decisions=[
            "8 平米 Pickup 店型,把单店投入压到 30 万(星巴克 300 万)",
            "小程序锁定用户 + 自提砍服务员,单店人力 1-2 人",
            "9 元券后价把星巴克'轻奢'打成'日常'",
        ],
        reflection="密度是餐饮最强的护城河。当 30 米就有瑞幸时,消费者不会再走 500 米去星巴克。"
                   "砍掉堂食不是'降级',是用更小场景换更高频次。",
        lessons=[
            "门店密度的边际成本要 5 倍低于同行才能形成垄断",
            "小程序 + 自提让'密度经济'和'人力成本'不再矛盾",
            "便宜 + 便利 > 品牌,这是中国市场的底层逻辑",
        ],
        tags=["密度", "小程序", "自提", "降本"],
        knowledge_ids=["unit_economics__增长模型", "revenue_model__订阅"],
        calculators=["break_even_point", "ltv_cac"],
        sources=["瑞幸 2023 财报", "虎嗅《瑞幸 2 万店》深度"],
    ),
    # ===== 转型类(2) =====
    CaseSpec(
        id="microsoft_cloud_pivot",
        title="微软云转型:从 Windows 授权到 Azure,纳德拉 10 年市值涨 10 倍",
        company="Microsoft",
        industry="软件/云",
        topic="转型",
        region="美国",
        period="2014-2024",
        background="2014 年纳德拉接任 CEO,Windows 授权收入见顶,启动'移动为先 / 云为先'战略,"
                   "砍掉 Nokia 手机业务,Azure 从 2015 年 $8B 营收冲到 2024 年 $75B(占总营收 33%),"
                   "Office 365 订阅化改造,2024 财年市值 $3.1T(2014 末 $300B),10 年涨 10 倍。",
        data={
            "azure_revenue_2015_billion_usd": 8.0,
            "azure_revenue_2024_billion_usd": 75.0,
            "market_cap_2014_billion_usd": 300,
            "market_cap_2024_billion_usd": 3100,
            "cloud_revenue_share_2024": 0.33,
        },
        decisions=[
            "砍 $7.6B 收购的 Nokia 手机业务,承认移动失败",
            "Office 强制转订阅(Office 365),从'一次性'到'持续'",
            "Azure 与 AWS 错位竞争(混合云 + 企业 IT 关系),不正面拼 IaaS 价格",
        ],
        reflection="纳德拉的转型核心不是'上云',是'订阅化'。Windows 授权是一次性现金奶牛,Azure + Office 365 是持续现金流。"
                   "一次性卖 $100 → 每年 $30 续 5 年,现金流 5 倍化但客户数相同,本质是商业模式的转变。",
        lessons=[
            "转型不是'新业务',是'老业务的商业化方式重做'",
            "承认失败要快(砍 Nokia 仅 1 年),止损节奏比转型速度更关键",
            "云转型要避开巨头正面价格战,找错位(混合云 / 行业云 / 私有化)",
        ],
        tags=["云转型", "订阅化", "商业模式", "管理层"],
        knowledge_ids=["revenue_model__订阅", "revenue_model__平台"],
        calculators=["ltv_cac", "payback_period"],
        sources=["Microsoft FY24 10-K", "Hit Refresh (Satya Nadella)"],
    ),
    CaseSpec(
        id="midea_digital_transformation",
        title="美的数字化:从'制造工厂'到'工业互联网',净利润 10 年 3.4 倍",
        company="美的集团",
        industry="家电制造",
        topic="转型",
        region="中国",
        period="2012-2023",
        background="2012 年方洪波接任董事长,启动'632 战略'(6 大运营系统 + 3 大管理平台 + 2 大门户),"
                   "2014 年引入 IBM 咨询,2018 年发布工业互联网平台 M.IoT,2023 年净利润 337 亿(2012 98 亿,3.4 倍)。"
                   "关键:制造端 C2M(用户直连制造)+ 销售端 T+3(以销定产,3 天交付)。",
        data={
            "net_profit_2012_billion_cny": 9.8,
            "net_profit_2023_billion_cny": 33.7,
            "growth_multiple_10y": 3.4,
            "t3_delivery_days": 3,
            "iot_devices_2023_million": 100,         # 美的物联网设备
        },
        decisions=[
            "T+3 订单驱动生产:从'压货模式'变'以销定产',库存周转从 60 天压到 30 天",
            "632 系统打通 ERP/MES/PLM,把决策权下放到事业部",
            "M.IoT 把工厂能力外部化(给其他制造业做工业互联网)",
        ],
        reflection="美的转型不是'互联网+',是'制造业自身的 IT 重构'。"
                   "核心 KPI 是库存周转天数,而非新业务收入。利润增长不是来自新业务,而是老业务的库存压缩。",
        lessons=[
            "传统行业转型 KPI 不要看新业务,看老业务的'人效/库存/周转'",
            "T+3 模式必须配合事业部制,否则推不动",
            "工业互联网是'把自己数字化后,服务别人',而非'做新平台'",
        ],
        tags=["数字化", "库存周转", "C2M", "工业互联网"],
        knowledge_ids=["cost_structure__规模经济", "cash_flow__营运资金"],
        calculators=["working_capital", "monthly_cash_flow"],
        sources=["美的 2023 年报", "方洪波《美的转型》"],
    ),
    # ===== 失败类(2) =====
    CaseSpec(
        id="ofo_burn_rate_collapse",
        title="ofo 退押金危机:日订单峰值 3200 万到 2000 万人排队退款",
        company="Ofo 小黄车",
        industry="共享出行",
        topic="失败",
        region="中国",
        period="2015-2021",
        background="2015 年北大校园起家,2017 年日订单峰值 3200 万,2018 年拿到阿里 + 滴滴 + 蚂蚁 14 亿美元(史上最高共享单车融资),"
                   "2018-2019 资金链断裂,2021 年排队退款人数突破 2000 万,押金 99-199 元/单车,理论应退 30-60 亿,实际无力兑付。",
        data={
            "peak_daily_orders_million": 32,         # 2017
            "total_funding_billion_usd": 1.4,
            "users_queuing_refund_2021_million": 20,
            "deposit_cny": 99,                       # 早期
            "deposit_late_cny": 199,
        },
        decisions=[
            "在 ofo + 摩拜 + 哈啰 三方大战中持续补贴,单车成本 300+ 单次收入 < 1 元",
            "挪用押金做新业务(广告/硬件),把押金池当现金流",
            "拒绝滴滴 + 蚂蚁 的合并方案,坚持独立",
        ],
        reflection="ofo 是'烧钱换规模 + 挪用押金'的双重失败。烧钱本身不致死(瑞幸也烧),致死的是把'用户押金'当融资来源。"
                   "一旦新业务不盈利 + 押金池被挪用,死亡螺旋即刻启动。",
        lessons=[
            "押金是用户的钱,不是你的融资款",
            "烧钱换规模的尽头是合并或倒闭,没有第三条路",
            "单车/充电宝等'高密度 + 低毛利'行业,毛利率 > 0 是底线",
        ],
        tags=["押金", "烧钱", "共享经济", "现金流"],
        knowledge_ids=["cash_flow__营运资金", "unit_economics__回收期"],
        calculators=["payback_period", "monthly_cash_flow"],
        sources=["界面新闻 ofo 调查 2021", "晚点 ofo 终局"],
    ),
    CaseSpec(
        id="evergrande_leverage_collapse",
        title="恒大 2.4 万亿负债:用 10 倍杠杆赌'房价永远涨'的清算",
        company="中国恒大",
        industry="房地产",
        topic="失败",
        region="中国",
        period="2016-2023",
        background="2017 年超越万科成为'宇宙第一房企',2018-2020 年总负债从 1.5 万亿冲到 2.4 万亿(占当年 GDP 2%),"
                   "2021 年 8.7 亿利息违约,2023 年港股清盘,负债总额 2.4 万亿创中国企业历史纪录。"
                   "资产端:土储 2.1 亿㎡(40% 在三四线);负债端:有息负债 8000 亿 + 应付账款 1 万亿 + 预售款 6000 亿。",
        data={
            "total_debt_2020_trillion_cny": 2.4,
            "gdp_share_2020": 0.02,
            "interest_only_default_2021_billion_cny": 8.7,
            "land_bank_million_sqm": 210,
            "tier_3_4_city_share": 0.4,
        },
        decisions=[
            "用商票 + 应付账款延长账期,把供应商当'无息贷款'",
            "2017-2020 持续高分红(许家印家族套现 500 亿),现金流吃紧时未停",
            "2020 年 1300 亿战投危机后未真正降杠杆,继续拿地",
        ],
        reflection="恒大是'杠杆 + 永涨预期'的清算。房地产的本质是金融,但金融的尽头是清算。"
                   "高分红 + 高负债 + 单一资产类别(住宅) = 三重脆弱性,任何一项出问题就是终局。",
        lessons=[
            "杠杆 + 单一资产类别 = 必爆(参考 2008 雷曼)",
            "账期 > 90 天的供应商应付账款是隐形负债,要计入总负债",
            "永涨预期是金融行业最大的杠杆,房企的杠杆率要看土储 2 年销售倍数",
        ],
        tags=["杠杆", "房地产", "资产质量", "清算"],
        knowledge_ids=["cash_flow__筹资", "roi__投资回报"],
        calculators=["roi", "payback_period", "working_capital"],
        sources=["恒大 2020 年报", "财新《恒大终局》"],
    ),
    # ===== 中国类(2) =====
    CaseSpec(
        id="alibaba_cloud_unit_economics",
        title="阿里云:从'双 11 内部用'到亚太第一,8 年从亏损到微利",
        company="阿里云",
        industry="云计算",
        topic="中国",
        region="中国",
        period="2009-2017",
        background="2009 年王坚启动阿里云,2013 年'5K 飞天集群'突破,"
                   "服务双 11 内部,2015 年公有云开始商业化,2017 年阿里云营收 133.9 亿(中国第一,占阿里总营收 5%),"
                   "运营利润率从 -50% 改善到 0% 附近,2023 财年盈利突破 10 亿。",
        data={
            "revenue_2017_billion_cny": 13.39,
            "revenue_share_in_alibaba_2017": 0.05,
            "operating_margin_2017": -0.20,
            "operating_margin_2023": 0.03,
            "asia_pacific_share_2017": 0.40,
        },
        decisions=[
            "先服务内部(双 11 / 菜鸟 / 蚂蚁),把技术跑通再外销",
            "IaaS 拼规模 + PaaS 拼行业方案,不和 AWS 拼基础功能",
            "政企客户专攻(部委/省级),单客 ASP 高于互联网客户 5 倍",
        ],
        reflection="阿里云证明'云业务的飞轮'需要 8-10 年。第一阶段练技术,第二阶段练商业化,第三阶段才盈利。"
                   "云不是互联网生意,是'重资产 + 长账期'的传统 IT 行业。",
        lessons=[
            "云业务起步要靠'自家业务跑通',不要直接外销",
            "政企客户的 ASP 是互联网客户的 5 倍,但销售周期长 3 倍",
            "云盈利节奏:第 1-5 年技术,第 6-8 年规模,第 9-10 年盈利",
        ],
        tags=["云", "B2B", "政企", "飞轮"],
        knowledge_ids=["revenue_model__平台", "cost_structure__规模经济"],
        calculators=["break_even_point", "roi"],
        sources=["阿里 2017 / 2023 财年报", "阿里云白皮书"],
    ),
    CaseSpec(
        id="pinduoduo_sink_market",
        title="拼多多下沉:用'百亿补贴'把 9.9 包邮做成 8 亿人的日常",
        company="拼多多",
        industry="电商",
        topic="中国",
        region="中国",
        period="2018-2023",
        background="2015 年成立,2018 年纳斯达克上市,2019 年推出'百亿补贴'主攻 iPhone/茅台等高客单,"
                   "完成'下沉 → 主流'反转,2020 年活跃买家 7.88 亿(超阿里 7.79 亿),"
                   "2023 年市值 $1800 亿,GMV 4.2 万亿(阿里 7 万亿),人均年消费 ¥3000+(阿里 ¥9000+)。",
        data={
            "active_buyers_2020_million": 788,
            "active_buyers_alibaba_2020_million": 779,
            "annual_spend_2023_cny": 3000,
            "alibaba_annual_spend_cny": 9000,
            "billion_subsidy_program_year": 2019,
        },
        decisions=[
            "微信生态起家,砍掉 APP 拉新成本(社交电商红利)",
            "百亿补贴 iPhone 茅台,用'绝对低价爆品'反向下沉",
            "多多买菜 / 多多视频,从电商切到生活,提高用户时长",
        ],
        reflection="拼多多的逆袭证明'流量结构变化 > 商业模式创新'。"
                   "微信 12 亿月活的红利,拼多多是第一个把它榨干的电商。下沉不是降级,是'流量结构 + 货品密度'的匹配。",
        lessons=[
            "社交关系链是电商的'免费渠道',别花钱买流量",
            "百亿补贴的本质是'亏本拉高端用户'反向教育下沉市场",
            "GMV 不是终极 KPI,年度人均消费 + 复购率才是",
        ],
        tags=["社交电商", "下沉市场", "百亿补贴", "微信生态"],
        knowledge_ids=["revenue_model__平台", "unit_economics__复购"],
        calculators=["ltv_cac", "payback_period"],
        sources=["拼多多 2020 / 2023 财报", "晚点《拼多多下沉》"],
    ),
]


# ---------- 工具 ----------
def slugify(text: str) -> str:
    """id 友好化(英文小写 + 下划线)"""
    s = text.strip().lower()
    s = re.sub(r"[\s/]+", "_", s)
    s = re.sub(r"[^\w\-]+", "", s)
    return s or "case"


# ---------- 入口 ----------
def build_index(specs: list[CaseSpec]) -> dict:
    by_topic: dict[str, int] = {}
    by_region: dict[str, int] = {}
    for s in specs:
        by_topic[s.topic] = by_topic.get(s.topic, 0) + 1
        by_region[s.region] = by_region.get(s.region, 0) + 1
    return {
        "schema_version": "0.1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(specs),
        "by_topic": by_topic,
        "by_region": by_region,
        "cases": [
            {
                "id": s.id,
                "title": s.title,
                "company": s.company,
                "industry": s.industry,
                "topic": s.topic,
                "region": s.region,
            }
            for s in specs
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="把 13 个盈利/定价案例入库到 content/cases/")
    parser.add_argument("--out", type=Path, default=Path("content/cases"),
                        help="输出 JSON 目录(默认 content/cases)")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    specs = SEED_CASES

    for spec in specs:
        out_path = args.out / f"{spec.id}.json"
        out_path.write_text(
            json.dumps(asdict(spec), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  ✅  {spec.id:36s} [{spec.topic:4s}/{spec.region:4s}] → {out_path.name}")

    index = build_index(specs)
    (args.out / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  📚  共 {index['total']} 个案例,覆盖 {len(index['by_topic'])} 类,索引 → {args.out / '_index.json'}")
    print(f"      主题: {', '.join(f'{k}={v}' for k, v in index['by_topic'].items())}")
    print(f"      地域: {', '.join(f'{k}={v}' for k, v in index['by_region'].items())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
