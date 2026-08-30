#!/usr/bin/env python3
"""
db_migrate_sqlite_to_pg.py · Phase 0 #5
======================================
把已有的 SQLite `data.db` 迁移到 PostgreSQL,为 Phase 1 FastAPI 骨架提供正式数据底座。

输入:  data.db (SQLite)  +  content/{knowledge,calculators,cases}/*.json  (Phase 0 #2/#3/#4 产物)
输出:  PostgreSQL 数据库初始化(表结构来自主计划 4.3)+ 灌库(知识图谱/计算器/案例)

设计原则 (Phase 0 阶段):
  - 0 外部依赖(只 stdlib),沿 calculators_seed.py / cases_seed.py 风格
  - 表结构 DDL 以字符串常驻,Phase 1 由 FastAPI lifespan 复用
  - SQLite → PG 的差异用 _SQL_TYPE_MAP 显式声明(SERIAL/JSONB/TEXT[] 等)
  - 灌库走 dry-run 模式(默认只打印 SQL,不真连 DB),真实灌库留到 Phase 0 #6 启用
  - 字段留 extension_points(red_flags/applications/explanation 等),Phase 3 由 LLM 补

扩展点 (留给后续 Phase):
  - Phase 0 #6:启用 --apply 模式,真实执行 CREATE TABLE + COPY JSON
  - Phase 1:FastAPI lifespan 调用 create_all() + load_seed_data() 完成启动自灌
  - Phase 2:加 business_accounts / profit_diagnoses / pricing_records / cash_flow_forecasts 写入路径
  - Phase 3:加 questions / users + 飞书 OAuth 注入

Usage:
  python3 scripts/db_migrate_sqlite_to_pg.py --dry-run          # 默认,只打印 SQL 不连 DB
  python3 scripts/db_migrate_sqlite_to_pg.py --dry-run --pg-url postgresql://localhost/profit
  python3 scripts/db_migrate_sqlite_to_pg.py --apply --pg-url postgresql://...   # 真实迁移(Phase 0 #6 启用)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------- 数据模型 ----------
@dataclass
class TableSpec:
    """单张目标表定义(主计划 4.3 的 PG 形态)"""
    name: str
    pk: str = "id"
    columns: list[tuple[str, str]] = field(default_factory=list)   # [(col_name, pg_type)]
    indexes: list[str] = field(default_factory=list)               # ["CREATE INDEX ..."]
    notes: str = ""


# ---------- SQLite → PG 类型映射 ----------
# 主计划 4.3 锁定的 PG 类型,这里集中声明,便于 Phase 1 lifespan 复用
_SQL_TYPE_MAP: dict[str, str] = {
    "INT": "SERIAL PRIMARY KEY" if False else "INTEGER",   # SERIAL 在建表句单独处理
    "TEXT": "TEXT",
    "REAL": "DOUBLE PRECISION",
    "BLOB": "BYTEA",
    "JSON": "JSONB",
    "JSONB": "JSONB",
    "TIMESTAMP": "TIMESTAMP",
    "TEXT[]": "TEXT[]",
    "INT[]": "INTEGER[]",
}


# ---------- 主计划 4.3 表结构(与盈利顾问开发架构与计划.md 严格一致)----------
TABLES: list[TableSpec] = [
    TableSpec(
        name="knowledge_points",
        columns=[
            ("name", "TEXT NOT NULL"),
            ("level", "TEXT"),                  # 入门/进阶/专业
            ("difficulty", "INTEGER"),          # 1-5
            ("description", "TEXT"),
            ("cases", "JSONB"),
            ("calculators", "JSONB"),
            ("tools", "JSONB"),
            ("red_flags", "JSONB"),              # 危险信号
            ("applications", "JSONB"),
            ("explanation", "JSONB"),            # 三件套讲解
            ("prerequisites", "INTEGER[]"),
            ("tags", "TEXT[]"),
        ],
        notes="Phase 0 #2 灌库源:content/knowledge/*.json",
    ),
    TableSpec(
        name="calculators",
        columns=[
            ("name", "TEXT"),
            ("category", "TEXT"),                # 利润/现金流/定价/投资/单位经济
            ("description", "TEXT"),
            ("inputs", "JSONB"),                 # 输入参数定义
            ("outputs", "JSONB"),                # 输出定义
            ("formula", "TEXT"),
            ("interpretation", "TEXT"),          # 解读规则
            ("example", "JSONB"),
            ("knowledge_ids", "INTEGER[]"),
        ],
        notes="Phase 0 #3 灌库源:content/calculators/*.json",
    ),
    TableSpec(
        name="profit_cases",
        columns=[
            ("title", "TEXT"),
            ("company", "TEXT"),
            ("industry", "TEXT"),
            ("topic", "TEXT"),                   # 定价/增长/转型/失败
            ("background", "TEXT"),
            ("data", "JSONB"),                   # 关键数字
            ("decisions", "JSONB"),
            ("reflection", "TEXT"),
            ("knowledge_ids", "INTEGER[]"),
        ],
        notes="Phase 0 #4 灌库源:content/cases/*.json",
    ),
    # Phase 2/3 留口(本 Phase 0 #5 只建表不灌数据)
    TableSpec(name="business_accounts", columns=[
        ("user_id", "INTEGER"), ("ts", "TIMESTAMP"),
        ("type", "TEXT"), ("category", "TEXT"),
        ("amount", "DOUBLE PRECISION"), ("note", "TEXT"),
    ], notes="Phase 2 启用"),
    TableSpec(name="profit_diagnoses", columns=[
        ("user_id", "INTEGER"), ("period", "TEXT"),
        ("inputs", "JSONB"), ("issues", "JSONB"),
        ("recommendations", "JSONB"), ("created_at", "TIMESTAMP"),
    ], notes="Phase 2 启用"),
    TableSpec(name="pricing_records", columns=[
        ("user_id", "INTEGER"), ("product", "TEXT"),
        ("cost", "DOUBLE PRECISION"), ("competitor_price", "DOUBLE PRECISION"),
        ("recommended_price", "DOUBLE PRECISION"),
        ("strategy", "TEXT"), ("created_at", "TIMESTAMP"),
    ], notes="Phase 2 启用"),
    TableSpec(name="cash_flow_forecasts", columns=[
        ("user_id", "INTEGER"), ("starting_balance", "DOUBLE PRECISION"),
        ("forecast_data", "JSONB"), ("risk_warnings", "JSONB"),
        ("created_at", "TIMESTAMP"),
    ], notes="Phase 2 启用"),
    TableSpec(name="questions", columns=[
        ("knowledge_id", "INTEGER REFERENCES knowledge_points(id)"),
        ("type", "TEXT"), ("difficulty", "INTEGER"),
        ("content", "TEXT"), ("answer", "TEXT"),
        ("analysis", "TEXT"), ("source", "TEXT"),
        ("created_at", "TIMESTAMP"),
    ], notes="Phase 3 启用"),
    TableSpec(name="users", columns=[
        ("open_id", "TEXT UNIQUE"), ("name", "TEXT"),
        ("role", "TEXT"), ("industry", "TEXT"),
        ("stage", "TEXT"), ("created_at", "TIMESTAMP"),
    ], notes="Phase 3 启用 + 飞书 OAuth"),
]


# ---------- DDL 生成 ----------
def build_create_sql(table: TableSpec) -> str:
    """生成单张表的 CREATE TABLE 语句(SERIAL PK + 列定义)"""
    cols = [f"  {c} {t}" for c, t in table.columns]
    head = f"CREATE TABLE IF NOT EXISTS {table.name} (\n"
    head += f"  {table.pk} SERIAL PRIMARY KEY,\n"
    body = ",\n".join(cols) + "\n);"
    return head + body


# ---------- 灌库(Phase 0 #6 启用)----------
def load_json_seed(content_dir: Path, kind: str) -> Iterable[dict]:
    """读 content/<kind>/_index.json 聚合索引,逐个加载 JSON 实体"""
    index_path = content_dir / kind / "_index.json"
    if not index_path.exists():
        return []
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    items = idx.get("items") or idx.get("calculators") or idx.get("cases") or []
    for slug in items:
        path = content_dir / kind / f"{slug}.json"
        if path.exists():
            yield json.loads(path.read_text(encoding="utf-8"))


# ---------- 入口 ----------
def main() -> int:
    ap = argparse.ArgumentParser(description="SQLite → PostgreSQL 迁移脚本骨架 (Phase 0 #5)")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="只打印 DDL,不连接任何 DB (默认)")
    ap.add_argument("--apply", action="store_true",
                    help="真实执行迁移(Phase 0 #6 启用,本骨架仅占位)")
    ap.add_argument("--sqlite", default="data.db", help="源 SQLite 文件路径")
    ap.add_argument("--pg-url", default="postgresql://localhost/profit", help="目标 PG 连接串")
    ap.add_argument("--content-dir", default="content", help="JSON 资产目录")
    args = ap.parse_args()

    print(f"[Phase 0 #5] db_migrate_sqlite_to_pg · mode={'apply' if args.apply else 'dry-run'}")
    print(f"  sqlite = {args.sqlite}")
    print(f"  pg_url = {args.pg_url}")
    print(f"  content_dir = {args.content_dir}")
    print()

    # 1) 打印所有 DDL
    for t in TABLES:
        print(f"-- {t.notes}")
        print(build_create_sql(t))
        print()

    # 2) dry-run 模式额外报告灌库源
    if not args.apply:
        for kind, label in [("knowledge", "知识图谱"), ("calculators", "计算器"), ("cases", "案例")]:
            n = sum(1 for _ in load_json_seed(Path(args.content_dir), kind))
            print(f"[seed] {label} 源: {n} 个 JSON 实体待灌库")
        print()
        print("[hint] 真实灌库请待 Phase 0 #6 启用 --apply (需先装 psycopg2-binary)")
        return 0

    # 3) --apply 占位(Phase 0 #6 启用)
    print("[TODO] --apply 真实迁移待 Phase 0 #6 实施,本骨架仅留口")
    print("  - 引入 psycopg2-binary 依赖")
    print("  - 读 SQLite 三表 → 转换 → COPY 到 PG")
    print("  - 校验行数 + 主键一致性")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
