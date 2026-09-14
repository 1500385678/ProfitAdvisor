# ProfitAdvisor

> **23-盈利-Profitability 行业 Web 项目** · ProfitabilityAdvisor
> 让每个生意人身边都有一位"巴菲特 + 一位 CFO + 一位精益运营专家"。

## 项目状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 0 - 资产盘点 | ✅ 已闭环 (6/6 复选框) | md → JSON、calcuators/cases/knowledge 三域满覆盖、跨域护栏稳定 |
| Phase 1 - MVP Web App | ⏳ 规划中 (0/7 复选框) | W08 后移节点 **0916 周三**由张勇拍板是否启动 |
| Phase 2 - 完整功能 | 📋 远期 (0/8 复选框) | 诊断 / 定价 / 预测 / 账目 |
| Phase 3 - AI 智能化 | 📋 远期 (0/6 复选框) | 三件套讲解 / 深度诊断 / 深度定价 |
| Phase 4 - 多端 + 商业化 | 📋 远期 | 小程序 / 桌面端 / BI 嵌入 |

## 技术栈

- **后端**:FastAPI (Python) · numpy_financial · pandas
- **前端**:React + TypeScript · Ant Design / shadcn/ui · ECharts
- **数据**:PostgreSQL (主) + SQLite (离线) · pgvector / Chroma
- **工程**:Docker Compose · GitHub Actions · Sentry + Prometheus
- **认证**:JWT + 飞书 OAuth

## 内容资产

| 域 | 数量 | 路径 | 护栏脚本 | 验证窗口 |
|----|------|------|----------|----------|
| **calculators** | 16 / 30+ (53.3%) | `content/calculators/` | `scripts/validate_calculators.py` | 132h+ 稳定 |
| **cases** | 13 / 400+ (3.25%) | `content/cases/` | `scripts/validate_cases.py` | 47h+ 稳定 |
| **knowledge** | 1 / 7 (14.3%) | `content/knowledge/` | `scripts/validate_knowledge.py` | 33h+ 稳定 |
| **md 源文件** | 1 / 7 | `content/md/` | — | 0827 起算未增 |

**三域跨域护栏覆盖率 100% (30/30 份 JSON)**。任何后续 T1 增量后只需一次 `validate_calculators && validate_cases && validate_knowledge` 即可守住 schema 一致性。

## 工程师卫生脚本

| 脚本 | 用途 | 落地日期 |
|------|------|----------|
| `scripts/md_to_json.py` | 7 份知识点 md → JSON | 2026-08-26 |
| `scripts/calculators_seed.py` | calculators 16 个种子入库 | 2026-08-28 |
| `scripts/cases_seed.py` | cases 13 个种子入库 | 2026-08-29 |
| `scripts/db_migrate_sqlite_to_pg.py` | SQLite → PG 迁移(主计划 4.3 锁 9 表 DDL + dry-run) | 2026-08-31 |
| `scripts/validate_calculators.py` | 7 项静态校验(calculators 域) | 2026-09-06 |
| `scripts/validate_cases.py` | 7 项静态校验(cases 域) | 2026-09-09 |
| `scripts/validate_knowledge.py` | 7 项静态校验(knowledge 域) | 2026-09-10 |

## 双 push 远端

- **Gitee**:`gitee.com/architectzy/ProfitAdvisor` (主备份,落后 0 闭合基线)
- **GitHub**:`github.com/1500385678/ProfitAdvisor` (公开,落后 0 闭合基线)
- **硬约束**:工作日 T1/T2/T4 commit 后立即双 push,任何巡检周期 github 落后 >0 立即报警

## 巡检日志

每日 02:40 cron 自动生成 `巡检-盈利-YYYYMMDD.md` 到 `.Log/` 目录,索引从 2026-08-26 起。当前 15 个工作日连续巡检(含 9/13 周日 cron 未触发的占位补录)。

## 快速开始 (Phase 1 启动后启用)

```bash
# Phase 1 启动前手动建表(W08 后移节点 0916 由张勇拍板)
pip install --user psycopg2-binary
python3 scripts/db_migrate_sqlite_to_pg.py --apply

# 内容数据查询(CLI/JSON,Phase 0 闭环已可跑)
python3 scripts/validate_calculators.py
python3 scripts/validate_cases.py
python3 scripts/validate_knowledge.py
```

---

**主计划**:`盈利顾问开发架构与计划.md` · **最新巡检**:`.Log/巡检-盈利-20260915.md` · **9/13 补录**:`.Log/巡检-盈利-20260913.md` · **维护**:张勇
