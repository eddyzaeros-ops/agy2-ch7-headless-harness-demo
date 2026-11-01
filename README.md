# Google Antigravity 2.0 (Agy 2.0) Headless 模式與 CL/CI 六大 Harness 實戰工作區 (`Ch7 工作區`)

本專案為《第 7 章：無為而治——Headless 模式與 CI/CD 集成》之完整可執行工程實例。展示如何在 **Google Antigravity 2.0 (`agy` CLI & Python SDK)** 的無頭（Headless）模式下，預先將 **6 大 Harness 元素** 宣告式封裝（Declarative Harness Packaging），並無縫接入本地 **CL（Change List / Pre-commit）** 與雲端 **CI（GitHub Actions Pipeline）** 自動化門禁。

---

## 📂 工作區完整目錄結構（所有數位文件皆存放於此）

```text
Ch7 工作區/
├── GEMINI.md                                      # [Harness 1: Rules] 專案全域憲法 (金融整數分、禁存 CVV、禁 f-string SQL)
├── AGENTS.md                                      # [Harness 1: Rules] 跨工具通用規則入口
├── mcp_config.json                                # [Harness 5: MCP] Agy 2.0 MCP 伺服器配置檔
├── prompts/
│   └── ci-headless-review-prompt.txt              # [執行控制] Headless 啟動時注入的任務專屬 System Prompt
├── schemas/
│   └── cl_review_report.schema.json               # [輸出格式控制] --json-schema 強制驗證的結構化輸出契約
├── .agents/                                       # Agy 2.0 工作區客製化根目錄 (VCS 團隊共享)
│   ├── hooks.json                                 # [Harness 6: Hooks] 生命週期強制攔截器 (SessionStart/PreToolUse/PostToolUse/Stop)
│   ├── skills.json                                # 顯式註冊工作區 Skills 路徑
│   ├── plugins.json                               # 顯式註冊工作區 Plugins 路徑
│   ├── skills/
│   │   └── payment-security-audit/
│   │       ├── SKILL.md                           # [Harness 2: Skill] 支付資安與 Schema 審查標準作業程序 (SOP)
│   │       ├── scripts/ast_pci_scanner.py         # Skill 內附的確定性 Python AST + Regex 靜態掃描器
│   │       └── references/owasp-pci-checklist.md  # Progressive Disclosure 按需讀取的合規手冊
│   ├── subagents/
│   │   └── pci-compliance-auditor.md              # [Harness 4: Sub-agent] 獨立 Context 的攻擊鏈與測試覆蓋分析子代理
│   └── plugins/
│       └── order-ci-harness/                      # [終極打包] 將 Rules + Skill + MCP + Hooks 封裝為單一 Plugin 單元
│           ├── plugin.json
│           ├── mcp_config.json
│           ├── hooks.json
│           └── rules/AGENTS.md
├── mcp_servers/
│   └── sqlite_schema_mcp.py                       # [Harness 5: MCP] 真實實作 JSON-RPC 2.0 over Stdio 的 SQLite Schema 伺服器
├── scripts/
│   ├── run_agy_headless_ci.sh                     # [Harness 3: Tools/CLI] 封裝 agy -p 四大維度參數的一鍵無頭啟動腳本
│   ├── agy_sdk_headless_runner.py                 # 6 大 Harness 全鏈路編排與 SDK 執行引擎
│   ├── local_cl_precommit_gate.py                 # 本地 CL 提交前 (Pre-commit) 自動攔截門禁腳本
│   └── hooks/                                     # [Harness 6: Hooks] 4 支真實可執行的生命週期 Hook 處理器
│       ├── on_session_start.py                    # SessionStart: 注入會話環境提醒 (injectSteps)
│       ├── pre_tool_security_guard.py             # PreToolUse: 硬性阻斷 rm -rf、讀取 .env、修改 schema.sql (decision=deny)
│       ├── post_tool_audit_logger.py              # PostToolUse: 自動寫入 JSONL 審計日誌
│       └── on_stop_quality_gate.py                # Stop: 主動修復模式下強制驗收單元測試，未通過則阻止退出 (decision=continue)
├── src/
│   ├── db/schema.sql                              # 生產環境真實資料表定義 (orders, payments, audit_logs)
│   └── order_service.py                           # 待審查的業務程式碼 (含故意設計的 SQLi、硬編碼金鑰、CVV 違規與欄位不匹配)
├── tests/
│   └── test_order_service.py                      # 包含 SQL Injection 負向攻擊測試的單元測試套件
├── reports/
│   ├── cl_review_report.json                      # 實機執行產出的 Headless 結構化 JSON 審查報告
│   └── pr_comment.md                              # 自動渲染並張貼至 GitHub PR 的 Markdown 審查報告
├── logs/
│   └── headless_hook_audit.jsonl                  # PostToolUse Hook 自動生成的工具呼叫審計軌跡 (對應第 7.10.5 節)
└── .github/workflows/
    └── agy-cl-ci-pipeline.yml                     # 跨階段 GitHub Actions 自動化 CL/CI 流水線
```

---

## 🛡️ 六大 Harness 元素在本實例中的具體分工與參數配置

| Harness 元素 | 專案實體檔案 | 在無頭 (Headless) 與 CL/CI 中的實際作用 | 對應啟動參數 / 機制 |
| :--- | :--- | :--- | :--- |
| **1. Rules (專案憲法)** | [`GEMINI.md`](./GEMINI.md)<br>[`AGENTS.md`](./AGENTS.md) | 定義金融金額必用整數分 `amount_cents`、PCI-DSS 禁存 `card_cvv`、禁 f-string 拼接 SQL。 | Agy 2.0 啟動時由 CWD 向上遍歷自動載入；額外指令透過 `prompts/ci-headless-review-prompt.txt` 注入。 |
| **2. Skill (領域技能包)** | [`.agents/skills/payment-security-audit/SKILL.md`](./.agents/skills/payment-security-audit/SKILL.md) | 封裝 4 步標準審查 SOP，並透過 [`ast_pci_scanner.py`](./.agents/skills/payment-security-audit/scripts/ast_pci_scanner.py) 執行確定性 AST 語法樹掃描。 | 透過 `.agents/skills.json` 註冊，採用 Progressive Disclosure 按需觸發。 |
| **3. Tools & Sandbox** | [`scripts/run_agy_headless_ci.sh`](./scripts/run_agy_headless_ci.sh)<br>[`schemas/cl_review_report.schema.json`](./schemas/cl_review_report.schema.json) | 限制無頭 Agent 僅能在唯讀規劃模式與 OS 沙箱中運行，並強制輸出符合 JSON Schema 的結構。 | `agy -p "..." --mode plan --sandbox --output-format json --json-schema ./schemas/cl_review_report.schema.json --print-timeout 3m0s` |
| **4. Sub-agent (子代理)** | [`.agents/subagents/pci-compliance-auditor.md`](./.agents/subagents/pci-compliance-auditor.md) | 委派獨立子代理執行負向安全單元測試 (`test_sql_injection_resilience`)，證實 `' OR '1'='1` 攻擊鏈可被觸發。 | 透過 `invoke_subagent` 工具在隔離 Context 中運行，僅將精簡結論傳回主 Agent。 |
| **5. MCP (外部資料源)** | [`mcp_config.json`](./mcp_config.json)<br>[`mcp_servers/sqlite_schema_mcp.py`](./mcp_servers/sqlite_schema_mcp.py) | 透過標準 JSON-RPC 2.0 over Stdio 查詢 `src/db/schema.sql`，抓出程式碼 `INSERT INTO payments` 使用了不存在的 `total_price` 與 `card_cvv` 欄位。 | 由 `mcp_config.json` 定義 Stdio 傳輸；環境變數設定 `MAX_MCP_OUTPUT_TOKENS=25000`。 |
| **6. Hooks (生命週期護欄)** | [`.agents/hooks.json`](./.agents/hooks.json)<br>[`scripts/hooks/*.py`](./scripts/hooks/) | `SessionStart` 注入提醒、`PreToolUse` 硬性攔截讀取 `.env` 或 `rm -rf` (`decision: deny`)、`PostToolUse` 寫入 JSONL 審計日誌、`Stop` 驗收測試。 | 由 `.agents/hooks.json` 綁定 4 個生命週期事件，不依賴大模型自制力，100% 確定性執行。 |

---

## 🚀 快速執行與驗證方式

```bash
# 1. 單獨驗證 MCP Server (JSON-RPC Schema 比對自檢)
python mcp_servers/sqlite_schema_mcp.py --self-test

# 2. 單獨驗證 Skill 內附的 AST + PCI-DSS 靜態掃描器
python .agents/skills/payment-security-audit/scripts/ast_pci_scanner.py src/

# 3. 執行完整的 Agy 2.0 Headless 6-Harness 審查編排器 (觀察者模式，產出 JSON 與 Markdown 報告)
python scripts/agy_sdk_headless_runner.py --gate-mode observer

# 4. 執行本地 CL Pre-commit 門禁模式 (發現 Critical 問題將回傳 Exit Code 1 攔截提交)
python scripts/local_cl_precommit_gate.py
```
