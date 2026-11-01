---
name: payment-security-audit
description: >-
  Use this skill whenever the agent is asked to review, audit, or validate code changes (CL/PR)
  in the Order & Payment microservice, especially in headless or CI/CD pipeline runs.
  Enforces PCI-DSS compliance, SQL injection prevention, integer cents arithmetic, and MCP database schema verification.
---

# Payment Security & Schema Audit Skill (`payment-security-audit`)

此技能定義了本專案在 **Google Antigravity 2.0 (Agy 2.0) Headless 模式** 與 **CL/CI 流水線**中執行自動化程式碼審查的標準作業程序（SOP）。

## 強制執行步驟（Mandatory Execution Workflow）

當此技能啟動時，Agent 必須依序完成以下 4 個步驟，不得跳過任何一步：

### Step 1: 執行確定性 AST 與 PCI-DSS 靜態掃描腳本
在進行大模型語義推理前，先使用 `run_command` 執行本技能內附的 Python 掃描器，快速定位硬編碼金鑰、f-string SQL 拼接與敏感欄位：

```bash
python .agents/skills/payment-security-audit/scripts/ast_pci_scanner.py src/
```

參考腳本原始碼：[ast_pci_scanner.py](./scripts/ast_pci_scanner.py)

### Step 2: 呼叫 MCP 伺服器核對資料庫真實 Schema
針對任何包含 `SELECT`、`INSERT`、`UPDATE` 的程式碼變更，**必須**呼叫 `sqlite-schema-mcp` 提供的工具：
1. 呼叫 `list_tables` 確認資料庫現有資料表清單。
2. 呼叫 `get_table_schema`（傳入 `table_name: "orders"` 與 `"payments"`），比對程式碼中的 SQL 欄位名稱與型別是否與 `src/db/schema.sql` 完全一致（特別注意金額欄位必須為 `amount_cents` 且不得存在 `card_cvv`）。

### Step 3: 委派 Sub-agent 進行跨檔案攻擊鏈與測試覆蓋分析
使用 `invoke_subagent`（類型選擇 `research` 或參照 `.agents/subagents/pci-compliance-auditor.md`）啟動唯讀子代理：
- **子代理任務 1**：檢查 `tests/` 目錄是否包含針對 SQL Injection 與 Schema 一致性的測試案例。
- **子代理任務 2**：根據 [owasp-pci-checklist.md](./references/owasp-pci-checklist.md) 驗證是否存在 N+1 查詢或未攔截的例外。

### Step 4: 產出符合 JSON Schema 的結構化審查報告
將 Step 1–3 的發現整合，嚴格按照 `schemas/cl_review_report.schema.json` 格式輸出 JSON。
- 若存在任何 `severity == "critical"` 的問題，`verdict` 必須設為 `"BLOCK"`。
- 若僅有 `warning`，`verdict` 設為 `"WARN"`。
- 若完全合規，`verdict` 設為 `"PASS"`。
