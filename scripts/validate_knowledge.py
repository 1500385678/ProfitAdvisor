#!/usr/bin/env python3
"""
validate_knowledge.py · 盈利知识图谱一致性校验
==============================================
扫描 content/knowledge/ 下所有 JSON,做静态校验,作为 Phase 0 → Phase 1
的工程师纪律(同 validate_calculators.py / validate_cases.py 7 项校验风格,
守 1 → 7 知识图谱 schema 一致,knowledge 第 2-7 份入库时不出现"图谱与
_index.json 漂移")。

校验项:
  1. 必填字段存在: id / name / level / difficulty / description / source_file
  2. id slug 唯一(节点 id 全目录唯一,源图谱短码前辍可见)
  3. level ∈ 白名单 3 档(入门 / 进阶 / 深度)
  4. difficulty ∈ [1, 5]
  5. list 字段 (tags / formulas / prerequisites / cases / calculators / tools
     / red_flags / applications) 允许空列表,但每项必须是非空字符串
  6. _index.json 的 total / by_category / nodes[].id 列表与实际文件一致
  7. _index.json 的每个 nodes[].id 必须在目录里能找到(无悬空)

退出码: 0 通过 / 1 有错误
输出: 简洁报告(总数/分类/错误清单)

Usage:
  python3 scripts/validate_knowledge.py
  python3 scripts/validate_knowledge.py --dir content/knowledge
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# ---------- 3 档认知难度白名单(主计划 4.2 知识图谱三档分层) ----------
VALID_LEVELS: set[str] = {"入门", "进阶", "深度"}

# ---------- 必填字段(节点顶层) ----------
REQUIRED_TOP_FIELDS: tuple[str, ...] = (
    "id", "name", "level", "difficulty", "description", "source_file",
)

# ---------- list 字段(允许空列表,但每项必须是非空字符串) ----------
LIST_FIELDS: tuple[str, ...] = (
    "tags", "formulas", "prerequisites", "cases",
    "calculators", "tools", "red_flags", "applications",
)


def load_knowledge(kb_dir: Path) -> tuple[list[dict], list[str]]:
    """加载目录里所有 knowledge JSON,返回 (nodes, errors)。

    knowledge 文件是节点 list(不是单 dict),逐个节点加入汇总列表。
    单文件 JSON 解析失败时,该文件跳过并加入 errors 列表。
    """
    nodes: list[dict] = []
    errors: list[str] = []
    for path in sorted(kb_dir.glob("*.json")):
        if path.name == "_index.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: JSON 解析失败 — {e}")
            continue
        if not isinstance(data, list):
            errors.append(f"{path.name}: 顶层必须是节点 list,实得 {type(data).__name__}")
            continue
        for n in data:
            n["_source_path"] = path.name  # 报告用
            nodes.append(n)
    return nodes, errors


def load_index(kb_dir: Path) -> dict | None:
    """加载 _index.json;不存在返回 None。"""
    index_path = kb_dir / "_index.json"
    if not index_path.exists():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def validate_one(node: dict) -> list[str]:
    """校验单个 knowledge 节点,返回错误列表(空 = 通过)。"""
    errs: list[str] = []
    nid = node.get("id", "<missing-id>")
    src = node.get("_source_path", "<?>")

    # 1. 必填顶层字段
    for field in REQUIRED_TOP_FIELDS:
        if field not in node:
            errs.append(f"  - [{src}] {nid}: 缺少必填字段: {field}")

    # 3. level 白名单
    level = node.get("level")
    if level is not None and level not in VALID_LEVELS:
        errs.append(f"  - [{src}] {nid}: level={level!r} 不在白名单 {sorted(VALID_LEVELS)}")

    # 4. difficulty ∈ [1, 5]
    diff = node.get("difficulty")
    if not isinstance(diff, int) or not (1 <= diff <= 5):
        errs.append(f"  - [{src}] {nid}: difficulty={diff!r} 不在 [1, 5]")

    # 5. list 字段:必须是 list,允许空,但每项非空字符串
    for field in LIST_FIELDS:
        val = node.get(field)
        if val is None:
            errs.append(f"  - [{src}] {nid}: 缺少 list 字段: {field}")
            continue
        if not isinstance(val, list):
            errs.append(f"  - [{src}] {nid}: {field} 必须是 list,实得 {type(val).__name__}")
            continue
        for i, item in enumerate(val):
            if not isinstance(item, str) or not item.strip():
                errs.append(
                    f"  - [{src}] {nid}: {field}[{i}]={item!r} 不是非空字符串"
                )

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 knowledge 知识图谱 schema 一致性")
    parser.add_argument(
        "--dir", default="content/knowledge",
        help="knowledge 目录路径(默认 content/knowledge)",
    )
    args = parser.parse_args()

    kb_dir = Path(args.dir)
    if not kb_dir.is_dir():
        print(f"❌ 目录不存在: {kb_dir}", file=sys.stderr)
        return 1

    nodes, load_errors = load_knowledge(kb_dir)
    index = load_index(kb_dir)

    # ---- 1-5 项:逐节点校验 ----
    per_node_errors: list[str] = []
    seen_ids: set[str] = set()
    dup_ids: list[str] = []
    for node in nodes:
        nid = node.get("id")
        # 2. id 唯一
        if nid in seen_ids:
            dup_ids.append(f"  - id 重复: {nid}")
        else:
            seen_ids.add(nid)
        per_node_errors.extend(validate_one(node))

    # ---- 6-7 项:与 _index.json 交叉对账 ----
    index_errors: list[str] = []
    if index is None:
        index_errors.append("  - _index.json 不存在,跳过 6/7 项交叉校验")
    else:
        actual_ids = sorted(seen_ids)
        index_ids = sorted(index.get("nodes", []))

        # 6.1 total_nodes 与实际节点数一致
        declared_total = index.get("total_nodes")
        if declared_total != len(actual_ids):
            index_errors.append(
                f"  - _index.json total_nodes={declared_total} 与实际节点数 {len(actual_ids)} 不一致"
            )

        # 6.2 by_category 之和应等于 total_nodes
        by_cat = index.get("by_category", {})
        if isinstance(by_cat, dict):
            cat_sum = sum(int(v) for v in by_cat.values() if isinstance(v, (int, float)))
            if cat_sum != len(actual_ids):
                index_errors.append(
                    f"  - _index.json by_category 之和={cat_sum} 与实际节点数 {len(actual_ids)} 不一致"
                )

        # 6.3 nodes[].id 列表完整且无遗漏
        if set(actual_ids) != set(index_ids):
            missing_in_index = sorted(set(actual_ids) - set(index_ids))
            extra_in_index = sorted(set(index_ids) - set(actual_ids))
            for mid in missing_in_index:
                index_errors.append(f"  - _index.json 缺少 id: {mid}")
            for eid in extra_in_index:
                # 7. 悬空 id
                index_errors.append(f"  - _index.json 悬空 id(目录里找不到): {eid}")

    # ---- 汇总输出 ----
    all_errors: list[str] = []
    all_errors.extend(load_errors)
    all_errors.extend(per_node_errors)
    all_errors.extend(dup_ids)
    all_errors.extend(index_errors)

    # 分类统计
    by_category: Counter[str] = Counter()
    by_level: Counter[str] = Counter()
    for n in nodes:
        sf = n.get("source_file", "未知")
        lv = n.get("level", "未知")
        by_category[sf] += 1
        by_level[lv] += 1

    print("=" * 60)
    print(f"knowledge 知识图谱 schema 校验报告")
    print("=" * 60)
    print(f"目录: {kb_dir}")
    print(f"节点总数: {len(nodes)} (覆盖 {len(by_category)} 个源图谱)")
    if by_category:
        print(f"by source_file:")
        for k in sorted(by_category):
            print(f"  - {k}: {by_category[k]}")
    if by_level:
        print(f"by level:")
        for k in sorted(by_level, key=lambda x: {"入门": 1, "进阶": 2, "深度": 3}.get(x, 99)):
            print(f"  - {k}: {by_level[k]}")
    print(f"id 唯一池: {len(seen_ids)} (重复 {len(dup_ids)})")
    print("-" * 60)

    if all_errors:
        print(f"❌ 校验失败,共 {len(all_errors)} 项问题:")
        for e in all_errors:
            print(e)
        return 1

    print("✅ 全部通过 · 7 项校验全过")
    print(f"  - 必填字段: {len(nodes)} 个节点字段完整")
    print(f"  - id 唯一: {len(seen_ids)} 个 slug 无重复")
    print(f"  - level 白名单: 全在 {sorted(VALID_LEVELS)}")
    print(f"  - difficulty ∈ [1,5]: 全部合规")
    print(f"  - list 字段非空: 8 类 list 全部类型正确")
    print(f"  - _index.json 一致: total/by_category/nodes 与实际对齐")
    print(f"  - 无悬空 id: index → 文件 双向无遗漏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
