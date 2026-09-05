#!/usr/bin/env python3
"""
validate_calculators.py · 盈利计算器一致性校验
================================================
扫描 content/calculators/ 下所有 JSON,做静态校验,作为 Phase 0 → Phase 1
的工程师纪律(类似 9/4 T1 把 multi_product_break_even 补回 seed 脚本那种
"闭环卫生")。

校验项:
  1. 必填字段存在: id / name / category / description / difficulty / formula / inputs / outputs
  2. id slug 唯一
  3. difficulty ∈ [1, 5]
  4. category ∈ 白名单 6 大类(利润/现金流/定价/投资/单位经济/增长)
  5. inputs[i] / outputs[i] 必填 name + label
  6. _index.json 的 total / by_category / calculators[].id 列表与实际文件一致
  7. _index.json 的每个 calculators[].id 必须在目录里能找到(无悬空)

退出码: 0 通过 / 1 有错误
输出: 简洁报告(总数/分类/错误清单)

Usage:
  python3 scripts/validate_calculators.py
  python3 scripts/validate_calculators.py --dir content/calculators
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# ---------- 6 大类白名单(主计划 4.2 财务计算六大类) ----------
VALID_CATEGORIES: set[str] = {"利润", "现金流", "定价", "投资", "单位经济", "增长"}

# ---------- 必填字段(顶层) ----------
REQUIRED_TOP_FIELDS: tuple[str, ...] = (
    "id", "name", "category", "description", "difficulty",
    "formula", "inputs", "outputs",
)

# ---------- inputs / outputs 项必填字段 ----------
REQUIRED_IO_FIELDS: tuple[str, ...] = ("name", "label")


def load_calculators(calc_dir: Path) -> tuple[list[dict], list[str]]:
    """加载目录里所有 calculator JSON,返回 (calcs, errors)。

    单文件 JSON 解析失败时,该文件跳过并加入 errors 列表。
    """
    calcs: list[dict] = []
    errors: list[str] = []
    for path in sorted(calc_dir.glob("*.json")):
        if path.name == "_index.json":
            continue
        try:
            calcs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: JSON 解析失败 — {e}")
    return calcs, errors


def load_index(calc_dir: Path) -> dict | None:
    """加载 _index.json;不存在返回 None。"""
    index_path = calc_dir / "_index.json"
    if not index_path.exists():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def validate_one(calc: dict) -> list[str]:
    """校验单个 calculator 定义,返回错误列表(空 = 通过)。"""
    errs: list[str] = []
    cid = calc.get("id", "<missing-id>")

    # 1. 必填顶层字段
    for field in REQUIRED_TOP_FIELDS:
        if field not in calc:
            errs.append(f"  - 缺少必填字段: {field}")

    # 2. category 白名单
    cat = calc.get("category", "")
    if cat and cat not in VALID_CATEGORIES:
        errs.append(f"  - category 非法: '{cat}'(白名单: {sorted(VALID_CATEGORIES)})")

    # 3. difficulty 范围
    diff = calc.get("difficulty")
    if isinstance(diff, int) and not (1 <= diff <= 5):
        errs.append(f"  - difficulty 越界: {diff}(应在 1-5)")

    # 4. inputs / outputs 项必填
    for kind in ("inputs", "outputs"):
        items = calc.get(kind, [])
        if not isinstance(items, list):
            errs.append(f"  - {kind} 不是 list")
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errs.append(f"  - {kind}[{idx}] 不是 dict")
                continue
            for f in REQUIRED_IO_FIELDS:
                if not item.get(f):
                    errs.append(f"  - {kind}[{idx}] 缺少字段: {f}")

    return ["[" + cid + "]" + e for e in errs]


def validate_index_consistency(
    calcs: list[dict],
    index: dict | None,
) -> list[str]:
    """校验 _index.json 与实际目录的一致性。"""
    if index is None:
        return ["  - _index.json 不存在(应自动生成)"]

    errs: list[str] = []
    actual_ids = {c["id"] for c in calcs}
    index_ids = {c["id"] for c in index.get("calculators", [])}

    # total 一致
    if index.get("total") != len(calcs):
        errs.append(
            f"  - _index.total = {index.get('total')}, 实际文件数 = {len(calcs)}"
        )

    # by_category 一致
    actual_by_cat: dict[str, int] = dict(Counter(c.get("category", "") for c in calcs))
    if index.get("by_category", {}) != actual_by_cat:
        errs.append(
            f"  - _index.by_category 失配: index={index.get('by_category')}, "
            f"actual={actual_by_cat}"
        )

    # id 集合一致
    if actual_ids - index_ids:
        errs.append(
            f"  - 实际文件但 _index 缺: {sorted(actual_ids - index_ids)}"
        )
    if index_ids - actual_ids:
        errs.append(
            f"  - _index 声明但实际文件缺: {sorted(index_ids - actual_ids)}"
        )

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="校验 content/calculators/ 下所有 JSON 的一致性"
    )
    parser.add_argument(
        "--dir", type=Path, default=Path("content/calculators"),
        help="计算器 JSON 目录(默认 content/calculators)",
    )
    args = parser.parse_args()

    calc_dir: Path = args.dir
    if not calc_dir.exists():
        print(f"❌ 目录不存在: {calc_dir}", file=sys.stderr)
        return 1

    calcs, load_errors = load_calculators(calc_dir)
    index = load_index(calc_dir)

    all_errors: list[str] = []
    all_errors.extend(load_errors)

    # 1. id 唯一性
    id_counter: Counter[str] = Counter(c.get("id", "<missing>") for c in calcs)
    dups = {k: v for k, v in id_counter.items() if v > 1}
    if dups:
        all_errors.append(f"  - id 重复: {dups}")

    # 2. 单个 calculator 校验
    for c in calcs:
        all_errors.extend(validate_one(c))

    # 3. _index.json 一致性
    all_errors.extend(validate_index_consistency(calcs, index))

    # ---------- 报告 ----------
    by_cat: dict[str, int] = dict(Counter(c.get("category", "?") for c in calcs))
    print(f"📐  validate_calculators")
    print(f"    目录: {calc_dir}")
    print(f"    文件数: {len(calcs)}(排除 _index.json)")
    print(f"    分类: {by_cat}")
    print(f"    _index.json: {'存在 ✓' if index else '缺失 ✗'}")
    print()

    if all_errors:
        print(f"❌  校验未通过,共 {len(all_errors)} 条问题:")
        for e in all_errors:
            print(e)
        return 1

    print(f"✅  校验通过 — {len(calcs)} 个计算器全部健康")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
