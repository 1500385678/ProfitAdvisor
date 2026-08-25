#!/usr/bin/env python3
"""
md_to_json.py · Phase 0 #1
================================
把 7 份知识点 markdown 解析为结构化 JSON,作为知识图谱初始数据。

输入 (7 份 md,固定在主计划 1.3 资产盘点):
  - revenue_model_knowledge.md       收入模型图谱
  - cost_structure_knowledge.md      成本结构图谱
  - profit_analysis_knowledge.md     利润分析图谱
  - cash_flow_knowledge.md           现金流图谱
  - pricing_strategy_knowledge.md    定价策略图谱
  - roi_knowledge.md                 投资回报图谱
  - unit_economics_knowledge.md      单位经济图谱

输出:
  - content/knowledge/<name>.json    单文件 JSON(可人工校对)
  - content/knowledge/_index.json    聚合索引(总览:数量/分类/标签)

设计原则 (Phase 0 阶段):
  - 0 外部依赖,只 stdlib,方便 Phase 0 早期直接跑
  - 解析策略保守:H1/H2 章节 → 节点;列表 → 标签;代码块 → 公式
  - 输出 schema 稳定,后续 Phase 1/2 可直接灌 PostgreSQL/向量库

扩展点 (留给后续 Phase):
  - 解析 "##" 段落时,识别 "案例:" / "计算器:" / "红旗:" 行,挂到对应字段
  - 支持 front-matter (YAML) 元数据
  - 接入 LLM 做语义补全(cases / calculators / tools 关联)

Usage:
  python3 scripts/md_to_json.py --src content/md --out content/knowledge
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


# ---------- 7 份核心知识图谱(主计划 1.3 资产盘点固定)----------
DEFAULT_KNOWLEDGE_FILES: list[dict] = [
    {"name": "revenue_model",     "title": "收入模型",   "category": "revenue"},
    {"name": "cost_structure",    "title": "成本结构",   "category": "cost"},
    {"name": "profit_analysis",   "title": "利润分析",   "category": "profit"},
    {"name": "cash_flow",         "title": "现金流",     "category": "cash_flow"},
    {"name": "pricing_strategy",  "title": "定价策略",   "category": "pricing"},
    {"name": "roi",               "title": "投资回报",   "category": "investment"},
    {"name": "unit_economics",    "title": "单位经济",   "category": "unit_economics"},
]


# ---------- 数据模型 ----------
@dataclass
class KnowledgeNode:
    """单个知识点节点(对应 md 中 H2 段落)"""
    id: str
    name: str
    level: str = "入门"          # 入门/进阶/专业 (后续可从难度推断)
    difficulty: int = 1          # 1-5
    description: str = ""
    tags: list[str] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)   # 代码块里的公式
    prerequisites: list[str] = field(default_factory=list)  # 关联到的前驱节点 id
    source_file: str = ""

    # 留给后续 Phase 补全的扩展字段
    cases: list[str] = field(default_factory=list)
    calculators: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    explanation: dict = field(default_factory=dict)     # 三件套: 数字/模型/行动


# ---------- 解析器 ----------
H2_PATTERN = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
H3_PATTERN = re.compile(r"^###\s+(?P<title>.+?)\s*$", re.MULTILINE)
CODE_BLOCK_PATTERN = re.compile(r"```[^\n]*\n(?P<body>.*?)```", re.DOTALL)
TAG_PATTERN = re.compile(r"^[-*]\s+(?P<tag>.+?)\s*$", re.MULTILINE)


def slugify(text: str) -> str:
    """简单 slug:id 友好化(中文保留,空白替为 _)"""
    s = text.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", s, flags=re.UNICODE)
    return s or "node"


def extract_formulas(md: str) -> list[str]:
    """提取代码块(Phase 0 视作公式/示例)"""
    return [m.group("body").strip() for m in CODE_BLOCK_PATTERN.finditer(md) if m.group("body").strip()]


def extract_tags(md: str) -> list[str]:
    """从列表项抓 tags(启发式:短文本 + 不含句号 → tag)"""
    tags: list[str] = []
    for m in TAG_PATTERN.finditer(md):
        item = m.group("tag").strip()
        # 启发:长度 ≤ 24 且不含中文句号 → 视作标签候选
        if len(item) <= 24 and "。" not in item and "." not in item.rstrip("."):
            tags.append(item)
    # 去重保序
    seen, uniq = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def parse_knowledge_md(md_text: str, file_meta: dict) -> list[KnowledgeNode]:
    """把一份 md 拆成 N 个 KnowledgeNode(按 H2 切片)"""
    nodes: list[KnowledgeNode] = []
    # 用 H2 切片,保留 H2/H3/正文/代码块
    h2_iter = list(H2_PATTERN.finditer(md_text))
    if not h2_iter:
        # 没 H2:整篇视作 1 个根节点
        nodes.append(KnowledgeNode(
            id=slugify(file_meta["name"]),
            name=file_meta["title"],
            description=md_text.strip()[:200],
            tags=extract_tags(md_text),
            formulas=extract_formulas(md_text),
            source_file=file_meta["name"],
        ))
        return nodes

    for i, m in enumerate(h2_iter):
        title = m.group("title").strip()
        start = m.end()
        end = h2_iter[i + 1].start() if i + 1 < len(h2_iter) else len(md_text)
        section = md_text[start:end]

        node = KnowledgeNode(
            id=slugify(f"{file_meta['name']}__{title}"),
            name=title,
            description=section.strip().splitlines()[0] if section.strip() else "",
            tags=extract_tags(section),
            formulas=extract_formulas(section),
            source_file=file_meta["name"],
        )
        # H3 → 视作 prerequisites 候选(在 Phase 1 由 graph_engine 解析为边)
        node.prerequisites = [slugify(h.group("title").strip()) for h in H3_PATTERN.finditer(section)]
        nodes.append(node)

    return nodes


# ---------- 入口 ----------
def build_index(all_nodes: list[KnowledgeNode], files_meta: list[dict]) -> dict:
    by_category: dict[str, int] = {}
    for n in all_nodes:
        cat = n.source_file  # Phase 0:source_file 当 category
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "schema_version": "0.1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_files": [f["name"] for f in files_meta],
        "total_nodes": len(all_nodes),
        "by_category": by_category,
        "nodes": [n.id for n in all_nodes],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse 7 份盈利知识图谱 md → JSON")
    parser.add_argument("--src", type=Path, default=Path("content/md"),
                        help="源 md 目录(默认 content/md)")
    parser.add_argument("--out", type=Path, default=Path("content/knowledge"),
                        help="输出 JSON 目录(默认 content/knowledge)")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    files_meta = DEFAULT_KNOWLEDGE_FILES
    all_nodes: list[KnowledgeNode] = []

    for meta in files_meta:
        md_path = args.src / f"{meta['name']}_knowledge.md"
        if not md_path.exists():
            print(f"  ⚠️  跳过:{md_path} 不存在(Phase 0 早期允许缺源)")
            continue
        text = md_path.read_text(encoding="utf-8")
        nodes = parse_knowledge_md(text, meta)
        # 单文件 JSON
        out_path = args.out / f"{meta['name']}.json"
        out_path.write_text(
            json.dumps([asdict(n) for n in nodes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  ✅  {meta['name']}: {len(nodes)} 节点 → {out_path}")
        all_nodes.extend(nodes)

    # 聚合索引
    index = build_index(all_nodes, files_meta)
    (args.out / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  📚 共 {index['total_nodes']} 节点,索引 → {args.out / '_index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
