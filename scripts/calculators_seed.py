#!/usr/bin/env python3
"""
calculators_seed.py · Phase 0 #3
=================================
把首批 10 个盈利计算器定义入库到 content/calculators/,作为 Phase 1 /calc API 的种子数据。

输入: 内置 10 个 CalculatorSpec(覆盖主计划 4.2 财务计算六大类:利润/现金流/定价/投资/单位经济/增长)
输出:
  - content/calculators/<id>.json   单个计算器定义
  - content/calculators/_index.json 聚合索引(分类/数量/标签)

设计原则 (Phase 0 阶段):
  - 0 外部依赖,只 stdlib,与 md_to_json.py 风格保持一致
  - 每个计算器 id 稳定 slug,便于 Phase 1 /calc/<id> 接口直接引用
  - 公式以字符串存储(inputs/outputs/formula),Phase 2 由 calc_engine.py 解析执行
  - 字段留 extension_points(cases[]/knowledge_ids[]/examples[]),Phase 1 可直接灌库

扩展点 (留给后续 Phase):
  - Phase 1:接入 FastAPI /calc/<id>/run,实际执行 inputs → outputs
  - Phase 2:补全 cases[]/examples[] (从 profitability_cases.md 抽取)
  - Phase 3:补全 explanation[] (三件套:数字/模型/行动) 由 LLM 自动生成

Usage:
  python3 scripts/calculators_seed.py --out content/calculators
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
class CalculatorSpec:
    """单个计算器定义(主计划 4.3 calculators 表的 JSON 形态)"""
    id: str
    name: str
    category: str                # 利润/现金流/定价/投资/单位经济/增长
    description: str
    difficulty: int = 1          # 1-5
    tags: list[str] = field(default_factory=list)
    inputs: list[dict] = field(default_factory=list)    # [{name, label, type, unit, required, default}]
    outputs: list[dict] = field(default_factory=list)   # [{name, label, unit}]
    formula: str = ""            # 公式文本(Phase 1 由 calc_engine 解析)
    interpretation: str = ""     # 解读规则(如何读懂输出)
    knowledge_ids: list[str] = field(default_factory=list)   # 关联知识点
    cases: list[str] = field(default_factory=list)           # 关联案例 id
    examples: list[dict] = field(default_factory=list)       # [{inputs: {}, outputs: {}, note: ""}]


# ---------- 10 个种子计算器(覆盖六大类)----------
SEED_CALCULATORS: list[CalculatorSpec] = [
    # ===== 利润类 =====
    CalculatorSpec(
        id="break_even_point",
        name="盈亏平衡点",
        category="利润",
        difficulty=2,
        description="计算覆盖固定成本所需的最小销量/销售额,常用于产品定价和销量目标拆解。",
        tags=["盈亏平衡", "固定成本", "变动成本", "保本"],
        inputs=[
            {"name": "fixed_cost",   "label": "固定成本",   "type": "number", "unit": "元",   "required": True},
            {"name": "price",        "label": "单价",       "type": "number", "unit": "元",   "required": True},
            {"name": "variable_cost","label": "单位变动成本","type": "number", "unit": "元",  "required": True},
        ],
        outputs=[
            {"name": "units",   "label": "保本销量",   "unit": "件"},
            {"name": "revenue", "label": "保本销售额", "unit": "元"},
            {"name": "contribution_margin", "label": "单位边际贡献", "unit": "元"},
        ],
        formula="units = fixed_cost / (price - variable_cost); revenue = units * price",
        interpretation="销量需 ≥ units 才能盈利;若当前销量 < units,要么提价要么压变动成本。",
        knowledge_ids=["revenue_model__收入公式", "profit_analysis__盈亏平衡"],
        examples=[
            {"inputs": {"fixed_cost": 50000, "price": 100, "variable_cost": 40},
             "outputs": {"units": 833.33, "revenue": 83333.33, "contribution_margin": 60},
             "note": "餐饮店固定成本 5 万,客单 100,食材 40 → 每天 28 单保本。"},
        ],
    ),
    CalculatorSpec(
        id="contribution_margin",
        name="边际贡献率",
        category="利润",
        difficulty=2,
        description="单位售价 - 单位变动成本 = 单位边际贡献;再除以单价即边际贡献率,反映每 1 元收入能贡献多少毛利。",
        tags=["边际贡献", "毛利率", "变动成本"],
        inputs=[
            {"name": "price",        "label": "单价",       "type": "number", "unit": "元", "required": True},
            {"name": "variable_cost","label": "单位变动成本","type": "number", "unit": "元", "required": True},
        ],
        outputs=[
            {"name": "contribution",      "label": "单位边际贡献", "unit": "元"},
            {"name": "contribution_rate", "label": "边际贡献率",   "unit": "%"},
        ],
        formula="contribution = price - variable_cost; rate = contribution / price",
        interpretation="边际贡献率 > 30% 通常算健康;过低(<20%)说明成本结构脆弱,涨价或降本压力大。",
        knowledge_ids=["profit_analysis__边际贡献"],
    ),
    # ===== 现金流类 =====
    CalculatorSpec(
        id="monthly_cash_flow",
        name="月度现金流预测",
        category="现金流",
        difficulty=3,
        description="基于期初余额 + 月度预计收入/支出,生成 12 月现金流轨迹,识别缺口月份。",
        tags=["现金流", "预测", "营运资金", "月度"],
        inputs=[
            {"name": "starting_balance", "label": "期初现金", "type": "number", "unit": "元", "required": True},
            {"name": "monthly_income",   "label": "月均收入", "type": "number", "unit": "元", "required": True},
            {"name": "monthly_expense",  "label": "月均支出", "type": "number", "unit": "元", "required": True},
            {"name": "months",           "label": "预测月数", "type": "number", "unit": "月", "default": 12, "required": False},
        ],
        outputs=[
            {"name": "ending_balance", "label": "期末余额", "unit": "元"},
            {"name": "lowest_month",   "label": "最低点月份", "unit": "月"},
            {"name": "is_negative",    "label": "是否穿底", "unit": "bool"},
        ],
        formula="ending = starting + (income - expense) * months; lowest = min(monthly_running)",
        interpretation="若 ending < 0 或中途穿底,需提前 3 个月融资/压缩支出。",
        knowledge_ids=["cash_flow__营运现金流"],
    ),
    CalculatorSpec(
        id="working_capital",
        name="营运资金需求",
        category="现金流",
        difficulty=3,
        description="计算维持日常经营所需的最低现金 = 应收账款 + 存货 - 应付账款。",
        tags=["营运资金", "应收", "应付", "存货"],
        inputs=[
            {"name": "accounts_receivable", "label": "应收账款", "type": "number", "unit": "元", "required": True},
            {"name": "inventory",           "label": "存货",     "type": "number", "unit": "元", "required": True},
            {"name": "accounts_payable",    "label": "应付账款", "type": "number", "unit": "元", "required": True},
        ],
        outputs=[
            {"name": "working_capital", "label": "营运资金", "unit": "元"},
            {"name": "days_cover",      "label": "覆盖天数", "unit": "天"},
        ],
        formula="wc = ar + inv - ap",
        interpretation="营运资金为正且 ≥ 3 个月支出的公司健康;为负说明靠应付账款/股东垫资在跑。",
        knowledge_ids=["cash_flow__营运资金"],
    ),
    # ===== 定价类 =====
    CalculatorSpec(
        id="cost_plus_pricing",
        name="成本加成定价",
        category="定价",
        difficulty=1,
        description="最基础定价法:售价 = 单位成本 × (1 + 加成率),适合制造业、零售业。",
        tags=["成本加成", "定价", "毛利"],
        inputs=[
            {"name": "unit_cost",   "label": "单位成本", "type": "number", "unit": "元", "required": True},
            {"name": "markup_rate", "label": "加成率",   "type": "number", "unit": "%",  "default": 30, "required": True},
        ],
        outputs=[
            {"name": "price",      "label": "建议售价", "unit": "元"},
            {"name": "gross_profit","label": "单位毛利","unit": "元"},
        ],
        formula="price = unit_cost * (1 + markup_rate / 100)",
        interpretation="零售业常用 30-50% 加成;餐饮食材成本 30-35% 对应 200% 加成。",
        knowledge_ids=["pricing_strategy__成本加成"],
    ),
    CalculatorSpec(
        id="value_based_pricing",
        name="价值定价锚点",
        category="定价",
        difficulty=4,
        description="基于客户感知价值反推售价:价值 = 客户获得的收益 × 客户认知度,适合高客单 B2B/SaaS。",
        tags=["价值定价", "感知价值", "B2B", "SaaS"],
        inputs=[
            {"name": "customer_value",    "label": "客户感知价值",   "type": "number", "unit": "元", "required": True},
            {"name": "value_capture_rate","label": "价值捕获率",     "type": "number", "unit": "%",  "default": 20, "required": True},
        ],
        outputs=[
            {"name": "anchor_price",  "label": "价值锚点价", "unit": "元"},
            {"name": "min_price",     "label": "保底价",     "unit": "元"},
        ],
        formula="anchor = customer_value * value_capture_rate / 100",
        interpretation="价值捕获率 10-30% 是 B2B SaaS 行业常见区间;低于 10% 说明价值未被认可。",
        knowledge_ids=["pricing_strategy__价值定价"],
    ),
    # ===== 投资类 =====
    CalculatorSpec(
        id="roi",
        name="投资回报率 ROI",
        category="投资",
        difficulty=1,
        description="(收益 - 成本) / 成本,衡量一笔投资或一个项目的回报效率。",
        tags=["ROI", "投资回报", "效率"],
        inputs=[
            {"name": "gain", "label": "总收益", "type": "number", "unit": "元", "required": True},
            {"name": "cost", "label": "总成本", "type": "number", "unit": "元", "required": True},
        ],
        outputs=[
            {"name": "roi",      "label": "投资回报率", "unit": "%"},
            {"name": "net_gain", "label": "净收益",     "unit": "元"},
        ],
        formula="roi = (gain - cost) / cost * 100",
        interpretation="ROI > 100% 即回本 2 倍;数字营销 ROI > 300% 才算合格,线下拓客 ROI > 200% 优秀。",
        knowledge_ids=["roi__投资回报"],
    ),
    CalculatorSpec(
        id="payback_period",
        name="投资回收期",
        category="投资",
        difficulty=2,
        description="用累计净现金流测算回本所需月数,直观判断投资风险窗口。",
        tags=["回收期", "投资风险", "现金流"],
        inputs=[
            {"name": "initial_investment", "label": "初始投资", "type": "number", "unit": "元", "required": True},
            {"name": "monthly_net_cash",   "label": "月均净现金", "type": "number", "unit": "元", "required": True},
        ],
        outputs=[
            {"name": "months",   "label": "回收期", "unit": "月"},
            {"name": "is_safe",  "label": "是否 < 12 月", "unit": "bool"},
        ],
        formula="months = initial_investment / monthly_net_cash",
        interpretation="回收期 ≤ 12 个月算优秀;≤ 24 个月可接受;> 36 个月有较大不确定性。",
        knowledge_ids=["roi__回收期"],
    ),
    # ===== 单位经济类 =====
    CalculatorSpec(
        id="ltv_cac",
        name="LTV / CAC 比",
        category="单位经济",
        difficulty=3,
        description="客户终身价值 LTV 与获客成本 CAC 之比,衡量增长是否健康。LTV/CAC ≥ 3 是 SaaS 健康线。",
        tags=["LTV", "CAC", "单位经济", "SaaS", "增长"],
        inputs=[
            {"name": "avg_revenue_per_user", "label": "ARPU(月)",   "type": "number", "unit": "元", "required": True},
            {"name": "gross_margin",         "label": "毛利率",     "type": "number", "unit": "%",  "required": True},
            {"name": "churn_rate",           "label": "月流失率",   "type": "number", "unit": "%",  "required": True},
            {"name": "cac",                  "label": "获客成本",   "type": "number", "unit": "元", "required": True},
        ],
        outputs=[
            {"name": "ltv",          "label": "客户终身价值", "unit": "元"},
            {"name": "ltv_cac_ratio","label": "LTV/CAC",     "unit": "倍"},
            {"name": "payback_months","label": "CAC 回收月数","unit": "月"},
        ],
        formula="ltv = (ARPU * gross_margin / 100) / (churn_rate / 100); payback = cac / (ARPU * gross_margin / 100)",
        interpretation="LTV/CAC < 1 烧钱;1-3 危险;≥ 3 健康;≥ 5 应该加大投放。",
        knowledge_ids=["unit_economics__LTV", "unit_economics__CAC"],
    ),
    # ===== 投资类 续 (10→11 · 2026-09-01 T1) =====
    CalculatorSpec(
        id="irr",
        name="内部收益率 IRR",
        category="投资",
        difficulty=3,
        description="使项目净现值 NPV = 0 的折现率,反映项目实际年化回报。考虑货币时间价值,比 ROI 更准确反映长周期投资的真实回报。",
        tags=["IRR", "内部收益率", "NPV", "贴现", "投资"],
        inputs=[
            {"name": "investment", "label": "初始投资",   "type": "number", "unit": "元", "required": True},
            {"name": "year1_cf",   "label": "第1年现金流", "type": "number", "unit": "元", "required": True},
            {"name": "year2_cf",   "label": "第2年现金流", "type": "number", "unit": "元", "required": True},
            {"name": "year3_cf",   "label": "第3年现金流", "type": "number", "unit": "元", "required": True},
            {"name": "year4_cf",   "label": "第4年现金流", "type": "number", "unit": "元", "required": True},
            {"name": "year5_cf",   "label": "第5年现金流", "type": "number", "unit": "元", "required": True},
        ],
        outputs=[
            {"name": "irr",         "label": "内部收益率",     "unit": "%"},
            {"name": "npv_check",   "label": "NPV 校验(应≈0)", "unit": "元"},
            {"name": "vs_roi_hint", "label": "与 ROI 差异提示", "unit": "str"},
        ],
        formula="求解 IRR 使 NPV = -investment + Σ(year_t_cf / (1+IRR)^t) = 0;Phase 1 由 calc_engine 牛顿迭代求解",
        interpretation="IRR > 15% 算优秀;8-15% 可接受;< 8% 不如余额宝。若 IRR 远低于 ROI,说明后期回款占比高,警惕资金时间成本;若 IRR 多次解则项目现金流形态异常,需重新审视投资逻辑。",
        knowledge_ids=["roi__内部收益率", "roi__NPV"],
        examples=[
            {"inputs": {"investment": 1000000, "year1_cf": 300000, "year2_cf": 400000, "year3_cf": 500000, "year4_cf": 200000, "year5_cf": 100000},
             "outputs": {"irr": 12.95, "npv_check": 0.0, "vs_roi_hint": "ROI≈50% 但 IRR≈13%,后期回款多,实际回报低于直觉"},
             "note": "100 万投资,5 年共回款 150 万,ROI=50% 但 IRR 仅 12.95%(因后期回款贴现损耗)。"},
        ],
    ),
    # ===== 增长类 =====
    CalculatorSpec(
        id="growth_funnel_conversion",
        name="增长漏斗转化率",
        category="增长",
        difficulty=2,
        description="分阶段计算漏斗转化率,识别增长瓶颈阶段(曝光→点击→注册→付费→留存)。",
        tags=["漏斗", "转化率", "增长", "留存"],
        inputs=[
            {"name": "impressions",   "label": "曝光量",   "type": "number", "unit": "次", "required": True},
            {"name": "clicks",        "label": "点击量",   "type": "number", "unit": "次", "required": True},
            {"name": "signups",       "label": "注册数",   "type": "number", "unit": "人", "required": True},
            {"name": "payers",        "label": "付费数",   "type": "number", "unit": "人", "required": True},
        ],
        outputs=[
            {"name": "ctr",            "label": "点击率",   "unit": "%"},
            {"name": "signup_rate",    "label": "注册转化率","unit": "%"},
            {"name": "paid_rate",      "label": "付费转化率","unit": "%"},
            {"name": "overall_rate",   "label": "总转化率", "unit": "%"},
            {"name": "bottleneck",     "label": "瓶颈阶段", "unit": "str"},
        ],
        formula="ctr = clicks/impressions; signup = signups/clicks; paid = payers/signups; overall = payers/impressions",
        interpretation="找到最低转化阶段即为瓶颈;行业基准:CTR 1-3%、注册 30-50%、付费 5-15%。",
        knowledge_ids=["unit_economics__增长模型"],
    ),
]


# ---------- 工具 ----------
def slugify(text: str) -> str:
    """id 友好化(英文小写 + 下划线)"""
    s = text.strip().lower()
    s = re.sub(r"[\s/]+", "_", s)
    s = re.sub(r"[^\w\-]+", "", s)
    return s or "calc"


# ---------- 入口 ----------
def build_index(specs: list[CalculatorSpec]) -> dict:
    by_category: dict[str, int] = {}
    for s in specs:
        by_category[s.category] = by_category.get(s.category, 0) + 1
    return {
        "schema_version": "0.1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(specs),
        "by_category": by_category,
        "calculators": [
            {"id": s.id, "name": s.name, "category": s.category, "difficulty": s.difficulty}
            for s in specs
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="把 10 个盈利计算器定义入库到 content/calculators/")
    parser.add_argument("--out", type=Path, default=Path("content/calculators"),
                        help="输出 JSON 目录(默认 content/calculators)")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    specs = SEED_CALCULATORS

    for spec in specs:
        out_path = args.out / f"{spec.id}.json"
        out_path.write_text(
            json.dumps(asdict(spec), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  ✅  {spec.id:30s} [{spec.category:6s}] → {out_path.name}")

    index = build_index(specs)
    (args.out / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  📐  共 {index['total']} 个计算器,覆盖 {len(index['by_category'])} 类,索引 → {args.out / '_index.json'}")
    print(f"      分类: {', '.join(f'{k}={v}' for k, v in index['by_category'].items())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
