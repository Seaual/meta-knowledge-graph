#!/usr/bin/env bash
# 运行测试并生成覆盖率报告

set -euo pipefail

# 检测测试框架
TEST_FRAMEWORK="jest"
if npm list vitest 2>/dev/null | grep -q vitest; then
  TEST_FRAMEWORK="vitest"
fi

echo "使用测试框架: $TEST_FRAMEWORK"

# 运行测试
if [ "$TEST_FRAMEWORK" = "vitest" ]; then
  npm test -- --run --coverage
else
  npm test -- --coverage
fi

echo "测试完成"