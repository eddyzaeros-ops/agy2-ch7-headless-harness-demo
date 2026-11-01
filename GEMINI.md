# Project Constitution & Engineering Rules (GEMINI.md)

本專案為「電商訂單與支付微服務（Order & Payment Service）」。所有 AI Agent（無論處於互動模式或 Headless 無頭自動化模式）在讀取、審查或修改本專案程式碼時，必須無條件遵守以下工程與資安規範：

## 1. 金融與支付安全紅線（PCI-DSS & OWASP Top 10）
- **嚴禁硬編碼憑證（No Hardcoded Secrets）**：任何 API Key（如 `sk_live_*`、`pk_live_*`）、資料庫密碼或 JWT Secret 必須透過 `os.environ.get()` 讀取，發現硬編碼一律判定為 `critical` 等級並阻斷 CL/PR 合併。
- **嚴禁儲存敏感卡號資訊（No CVV Storage）**：依據 PCI-DSS 第 3.2 條規範，系統在任何情況下（含變數、日誌、資料庫 INSERT/UPDATE）皆**嚴禁接收或儲存信用卡安全碼（`card_cvv` / `cvv`）**。發現即判定為 `critical`。
- **禁止 SQL 字串拼接（No SQL Injection）**：所有 SQLite / PostgreSQL 查詢必須使用參數化佔位符（`?` 或 `$1`），嚴禁使用 Python `f-string`、`%` 或 `.format()` 拼接 SQL 語句。發現即判定為 `critical`。

## 2. 資料庫與金額型別規範
- **金額必須使用整數分（Integer Cents）**：所有金額運算與資料庫欄位必須使用整數型別（如 `amount_cents: int`），嚴禁使用 `float` 進行貨幣計算以避免浮點數精度誤差。發現使用 `float` 處理金額判定為 `warning`。
- **強制核對 MCP 真實 Schema**：任何涉及 SQL 讀寫的程式碼變更，Agent **必須**呼叫 `sqlite-schema-mcp` 提供的 `get_table_schema` 工具核對資料表真實欄位名稱與型別，不得僅憑程式碼變數名稱猜測。

## 3. Headless 審查與修復作業程序
- 當執行程式碼審查任務時，必須啟用工作區技能 `payment-security-audit`（位於 `.agents/skills/payment-security-audit/SKILL.md`），先執行其內附之靜態 AST 掃描腳本，再結合語義分析與子代理（Sub-agent）委派完成審查。
- 當輸出格式要求為 JSON 時，必須嚴格遵循 `schemas/cl_review_report.schema.json` 定義之結構，確保下游 CI 門禁腳本可直接解析。
