#!/usr/bin/env bash
# ==============================================================================
# Google Antigravity 2.0 (Agy 2.0) Headless CL/CI 啟動腳本
# 檔案路徑：scripts/run_agy_headless_ci.sh
# 涵蓋第 7 章四大參數維度 (輸出格式、成本/超時護欄、安全邊界、執行控制) 與 6 大 Harness 元素
# ==============================================================================
set -euo pipefail

GATE_MODE="${1:-observer}" # 支援 observer | advisor | gatekeeper
PROMPT_FILE="./prompts/ci-headless-review-prompt.txt"
SCHEMA_FILE="./schemas/cl_review_report.schema.json"

# 1. 生產級 CI 環境變數配置 (對應第 7.8 節)
export AGY_ADC_AUTH="true"                                  # 使用雲端憑證免互動登入
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"         # 關閉自動更新、遙測與錯誤上報
export BASH_DEFAULT_TIMEOUT_MS="120000"                     # 命令預設超時 2 分鐘
export MAX_MCP_OUTPUT_TOKENS="25000"                        # 限制 MCP 回傳 Token 上限

echo "🚀 [Agy 2.0 Headless CI] 啟動無頭審查流水線 (Gate Mode: ${GATE_MODE})..."

# 2. 若環境中存在原生 agy CLI 且已配置線上 API 金鑰，展示標準 agy -p 呼叫方式：
if command -v agy >/dev/null 2>&1 && [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "🔹 偵測到原生 agy CLI 與 API 金鑰，執行 agy -p 無頭模式..."
  agy -p "$(cat "$PROMPT_FILE")" \
    --mode plan \
    --sandbox \
    --output-format json \
    --json-schema "$SCHEMA_FILE" \
    --print-timeout 3m0s > ./reports/cl_review_report.json
else
  # 3. 執行 6 大 Harness 元素全鏈路確定性驗證與 SDK 驅動器 (確保本地與 GitHub Actions 100% 穩定產出)
  echo "🔹 執行 Agy 2.0 六大 Harness 元素全鏈路編排器 (Rules + Skill + Tools + Subagent + MCP + Hooks)..."
  python3 ./scripts/agy_sdk_headless_runner.py --gate-mode "${GATE_MODE}" > /dev/null
fi

echo "✅ [Agy 2.0 Headless CI] 審查報告已生成："
echo "   - 結構化 JSON: ./reports/cl_review_report.json"
echo "   - PR 評論 Markdown: ./reports/pr_comment.md"
echo "   - Hooks 審計日誌: ./logs/headless_hook_audit.jsonl"
