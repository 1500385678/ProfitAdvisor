#!/usr/bin/env bash
# scripts/double_push.sh
# 工程师卫生:封装 gitee + github 双 push,带 rev-list 实时验证
# 落地日期:2026-09-19(T4 周末补录,9/20 周日 cron 实执行)
# 解决:README L51 硬约束"工作日 T1/T2/T4 commit 后立即双 push,任何巡检周期 github 落后 >0 立即报警"
# 用法:bash scripts/double_push.sh
# 前置:仓库已配置 gitee + github 远端(详见 git remote -v)

set -u  # 不开 -e:需要让 push 失败可观察,且第一个 push 成功后第二个不应被中断
set -o pipefail

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 切到仓库根目录(脚本所在目录的上一级)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || {
  echo -e "${RED}[FATAL]${NC} 无法切到仓库根目录($SCRIPT_DIR/..)"
  exit 1
}

BRANCH="${1:-main}"

echo "==> 双 push 启动 · 分支: $BRANCH · 工作目录: $(pwd)"
echo "==> HEAD: $(git rev-parse --short HEAD) · $(git log -1 --pretty=format:'%s')"
echo

# 1. 推送 Gitee(主备份,优先,失败立即终止)
echo "==> [1/4] push Gitee ..."
if ! git push -q -f gitee "$BRANCH" 2>&1; then
  echo -e "${RED}[FAIL]${NC} Gitee push 失败,终止流程"
  echo "    排查:git remote -v / 网络 / Gitee 凭据"
  exit 2
fi
echo -e "    ${GREEN}OK${NC}"
echo

# 2. 推送 GitHub(公开仓库,慢,允许超时)
echo "==> [2/4] push GitHub(允许 30s 超时)..."
GITHUB_PUSH_OK=0
# 用 timeout 包裹,允许慢速网络;git push 自身支持 Ctrl-C 中断
if timeout 30 git push -q -f github "$BRANCH" 2>&1; then
  echo -e "    ${GREEN}OK${NC}"
  GITHUB_PUSH_OK=1
else
  GITHUB_EXIT=$?
  echo -e "    ${YELLOW}[WARN]${NC} GitHub push 失败/超时(exit=$GITHUB_EXIT),不阻塞流程"
  echo "    后续可单独重试:git push -q -f github $BRANCH"
fi
echo

# 3. rev-list 实时验证(无论 github 是否成功,都跑一次双仓库落后比对)
echo "==> [3/4] rev-list 实时验证(本地 vs gitee vs github)..."
LOCAL_HEAD=$(git rev-parse "$BRANCH")

GITEE_BEHIND=$(git rev-list --left-right --count "$BRANCH"...gitee/"$BRANCH" 2>/dev/null | awk '{print $1}')
GITEE_BEHIND="${GITEE_BEHIND:-?}"
GITHUB_BEHIND=$(git rev-list --left-right --count "$BRANCH"...github/"$BRANCH" 2>/dev/null | awk '{print $1}')
GITHUB_BEHIND="${GITHUB_BEHIND:-?}"
GITEE_VS_GITHUB=$(git rev-list --left-right --count gitee/"$BRANCH"...github/"$BRANCH" 2>/dev/null | awk '{print $1}')

printf "    本地 main   HEAD: %s\n" "$LOCAL_HEAD"
printf "    gitee   落后: %s commit(s)\n" "$GITEE_BEHIND"
printf "    github  落后: %s commit(s)\n" "$GITHUB_BEHIND"
printf "    gitee vs github(gitee 领先): %s commit(s)\n" "$GITEE_VS_GITHUB"
echo

# 4. 验收
echo "==> [4/4] 验收 ..."
EXIT_CODE=0
if [ "$GITEE_BEHIND" != "0" ]; then
  echo -e "    ${RED}[FAIL]${NC} gitee 落后 $GITEE_BEHIND commit(s)(硬约束 README L51)"
  EXIT_CODE=3
fi
if [ "$GITHUB_BEHIND" != "0" ]; then
  echo -e "    ${RED}[FAIL]${NC} github 落后 $GITHUB_BEHIND commit(s)(硬约束 README L51)"
  EXIT_CODE=4
fi

if [ "$EXIT_CODE" -eq 0 ]; then
  echo -e "    ${GREEN}双 push 0/0 闭合${NC} · gitee 与 github 均已同步"
  if [ "$GITHUB_PUSH_OK" -eq 0 ]; then
    echo -e "    ${YELLOW}注意${NC}:GitHub 本次 push 失败,但 rev-list 校验通过(可能是上轮 push 已闭合)"
    EXIT_CODE=0  # 不阻塞,已经 0/0 闭合
  fi
else
  echo -e "    ${RED}双 push 未闭合${NC},见上方 [FAIL] 项"
fi

echo
echo "==> 双 push 流程结束 · exit=$EXIT_CODE"
exit $EXIT_CODE