# OWASP Top 10 & PCI-DSS 4.0 Reference Checklist

本參考文件僅在 `payment-security-audit` Skill 需要深度比對合規條文時由 Agent 按需讀取（Progressive Disclosure，不預設佔用主 Context Window）。

## 1. PCI-DSS v4.0 Requirement 3.2 (Sensitive Authentication Data)
- **3.2.1**: 交易授權完成後，嚴禁留存任何敏感驗證資料（SAD），即便經過加密亦不可儲存。
- **3.2.2**: 信用卡驗證碼（CAV2/CVC2/CVV2/CID，即卡背 3 碼或卡面 4 碼）在任何情況下皆不可寫入關聯式資料庫、NoSQL、日誌檔或稽核軌跡。

## 2. OWASP A03:2021 - Injection (SQL Injection)
- Python `sqlite3` 驅動程式必須使用 `?` 參數化查詢（Parameterized Query）或 `:name` 具名佔位符。
- 禁止任何形式的字串格式化（`f"..."`、`"...".format()`、`"%s" % ...`）直接進入 `cursor.execute()`。

## 3. OWASP A07:2021 - Identification and Authentication Failures (Hardcoded Secrets)
- 生產環境金鑰（如 `sk_live_*`）不得出現在原始碼中。應搭配 Git Pre-commit Hook 與 CI Gate 在合併前阻斷。
