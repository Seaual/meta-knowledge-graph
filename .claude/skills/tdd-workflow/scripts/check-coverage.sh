#!/usr/bin/env bash
# 检查覆盖率是否达到阈值

set -euo pipefail

THRESHOLD="${1:-80}"

# 查找覆盖率文件
COVERAGE_FILE=""
if [ -f "coverage/coverage-summary.json" ]; then
  COVERAGE_FILE="coverage/coverage-summary.json"
elif [ -f "coverage/lcov-report/lcov.info" ]; then
  echo "从 lcov.info 解析覆盖率..."
  # 简单解析 lcov 格式
  LINES_FOUND=$(grep -c "^LF:" coverage/lcov-report/lcov.info 2>/dev/null || echo "0")
  LINES_HIT=$(grep -c "^LH:" coverage/lcov-report/lcov.info 2>/dev/null || echo "0")
  if [ "$LINES_FOUND" -gt 0 ]; then
    LINE_COVERAGE=$(echo "scale=2; $LINES_HIT * 100 / $LINES_FOUND" | bc)
    echo "行覆盖率: ${LINE_COVERAGE}%"
    if (( $(echo "$LINE_COVERAGE >= $THRESHOLD" | bc -l) )); then
      echo "覆盖率达标（阈值: ${THRESHOLD}%）"
      exit 0
    else
      echo "覆盖率不足（阈值: ${THRESHOLD}%）"
      exit 1
    fi
  fi
fi

if [ -z "$COVERAGE_FILE" ] || [ ! -f "$COVERAGE_FILE" ]; then
  echo "错误：覆盖率文件不存在，请先运行测试"
  exit 1
fi

# 从 JSON 提取行覆盖率（Jest 格式）
LINE_COVERAGE=$(cat "$COVERAGE_FILE" | grep -o '"lines":{[^}]*}' | grep -o '[0-9]*\.[0-9]*' | head -1)

echo "行覆盖率: ${LINE_COVERAGE}%"

if (( $(echo "$LINE_COVERAGE >= $THRESHOLD" | bc -l) )); then
  echo "覆盖率达标（阈值: ${THRESHOLD}%）"
  exit 0
else
  echo "覆盖率不足（阈值: ${THRESHOLD}%）"
  exit 1
fi