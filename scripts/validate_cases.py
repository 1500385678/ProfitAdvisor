#!/usr/bin/env python3
"""
validate_cases.py · 盈利案例库一致性校验
========================================
扫描 content/cases/ 下所有 JSON,做静态校验,作为 Phase 0 → Phase 1
的工程师纪律(同 validate_calculators.py 7 项校验风格,守 13 → 400+
案例库 schema 一致)。

校验项:
  1. 必填字段存在: id / title / company / industry / topic / region
  2. id slug 唯一
  3. topic ∈ 白名单 5 大类(定价/增长/转型/失败/中国)
  4. region ∈ 白名单 4 大区(中国/美国/欧洲/全球)
  5. list 字段 (decisions / lessons / tags / knowledge_ids / calculators / sources)
     每项非空字符串
  6. _index.json 的 total / by_topic / by_region / cases[].id 列表与实际文件一致
  7. _index.json 的每个 cases[].id 必须在目录里能找到(无悬空)

退出码: 0 通过 / 1 有错误
输出: 简洁报告(总数/分类/错误清单)

Usage:
  python3 scripts/validate_cases.py
  python3 scripts/validate_cases.py --dir content/cases
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# ---------- 5 大类白名单(主计划 4.2 案例库五大类) ----------
VALID_TOPICS: set[str] = {"定价", "增长", "转型", "失败", "中国"}

# ---------- 4 大区白名单 ----------
VALID_REGIONS: set[str] = {"中国", "美国", "欧洲", "全球"}

# ---------- 必填字段(顶层) ----------
REQUIRED_TOP_FIELDS: tuple[str, ...] = (
    "id", "title", "company", "industry", "topic", "region",
)

# ---------- list 字段(每项必须是非空字符串) ----------
LIST_FIELDS: tuple[str, ...] = (
    "decisions", "lessons", "tags", "knowledge_ids", "calculators", "sources",
)


def load_cases(case_dir: Path) -> tuple[list[dict], list[str]]:
    """加载目录里所有 case JSON,返回 (cases, errors)。

    单文件 JSON 解析失败时,该文件跳过并加入 errors 列表。
    """
    cases: list[dict] = []
    errors: list[str] = []
    for path in sorted(case_dir.glob("*.json")):
        if path.name == "_index.json":
            continue
        try:
            cases.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: JSON 解析失败 — {e}")
    return cases, errors


def load_index(case_dir: Path) -> dict | None:
    """加载 _index.json;不存在返回 None。"""
    index_path = case_dir / "_index.json"
    if not index_path.exists():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def validate_one(case: dict) -> list[str]:
    """校验单个 case 定义,返回错误列表(空 = 通过)。"""
    errs: list[str] = []
    cid = case.get("id", "<missing-id>")

    # 1. 必填顶层字段
    for field in REQUIRED_TOP_FIELDS:
        if field not in case:
            errs.append(f"  - 缺少必填字段: {field}")

    # 2. topic 白名单
    topic = case.get("topic", "")
    if topic and topic not in VALID_TOPICS:
        errs.append(
            f"  - topic 非法: '{topic}'(白名单: {sorted(VALID_TOPICS)})"
        )

    # 3. region 白名单
    region = case.get("region", "")
    if region and region not in VALID_REGIONS:
        errs.append(
            f"  - region 非法: '{region}'(白名单: {sorted(VALID_REGIONS)})"
        )

    # 4. list 字段必填且每项非空字符串
    for field in LIST_FIELDS:
        items = case.get(field, [])
        if not isinstance(items, list):
            errs.append(f"  - {field} 不是 list")
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, str):
                errs.append(f"  - {field}[{idx}] 不是字符串: {type(item).__name__}")
                continue
            if not item.strip():
                errs.append(f"  - {field}[{idx}] 是空字符串")

    return ["[" + cid + "]" + e for e in errs]


def validate_index_consistency(
    cases: list[dict],
    index: dict | None,
) -> list[str]:
    """校验 _index.json 与实际目录的一致性。"""
    if index is None:
        return ["  - _index.json 不存在(应自动生成)"]

    errs: list[str] = []
    actual_ids = {c["id"] for c in cases}
    index_ids = {c["id"] for c in index.get("cases", [])}

    # total 一致
    if index.get("total") != len(cases):
        errs.append(
            f"  - _index.total = {index.get('total')}, 实际文件数 = {len(cases)}"
        )

    # by_topic 一致
    actual_by_topic: dict[str, int] = dict(
        Counter(c.get("topic", "") for c in cases)
    )
    if index.get("by_topic", {}) != actual_by_topic:
        errs.append(
            f"  - _index.by_topic 失配: index={index.get('by_topic')}, "
            f"actual={actual_by_topic}"
        )

    # by_region 一致
    actual_by_region: dict[str, int] = dict(
        Counter(c.get("region", "") for c in cases)
    )
    if index.get("by_region", {}) != actual_by_region:
        errs.append(
            f"  - _index.by_region 失配: index={index.get('by_region')}, "
            f"actual={actual_by_region}"
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
        description="校验 content/cases/ 下所有 JSON 的一致性"
    )
    parser.add_argument(
        "--dir", type=Path, default=Path("content/cases"),
        help="案例 JSON 目录(默认 content/cases)",
    )
    args = parser.parse_args()

    case_dir: Path = args.dir
    if not case_dir.exists():
        print(f"❌ 目录不存在: {case_dir}", file=sys.stderr)
        return 1

    cases, load_errors = load_cases(case_dir)
    index = load_index(case_dir)

    all_errors: list[str] = []
    all_errors.extend(load_errors)

    # 1. id 唯一性
    id_counter: Counter[str] = Counter(c.get("id", "<missing>") for c in cases)
    dups = {k: v for k, v in id_counter.items() if v > 1}
    if dups:
        all_errors.append(f"  - id 重复: {dups}")

    # 2. 单个 case 校验
    for c in cases:
        all_errors.extend(validate_one(c))

    # 3. _index.json 一致性
    all_errors.extend(validate_index_consistency(cases, index))

    # ---------- 报告 ----------
    by_topic: dict[str, int] = dict(Counter(c.get("topic", "?") for c in cases))
    by_region: dict[str, int] = dict(Counter(c.get("region", "?") for c in cases))
    print("📋  validate_cases")
    print(f"    目录: {case_dir}")
    print(f"    文件数: {len(cases)}(排除 _index.json)")
    print(f"    by_topic: {by_topic}")
    print(f"    by_region: {by_region}")
    print(f"    _index.json: {'存在 ✓' if index else '缺失 ✗'}")
    print()

    if all_errors:
        print(f"❌  校验未通过,共 {len(all_errors)} 条问题:")
        for e in all_errors:
            print(e)
        return 1

    print(f"✅  校验通过 — {len(cases)} 个案例全部健康")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
