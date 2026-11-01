# Agent Guidelines (AGENTS.md)

請參照同目錄下之 `@[GEMINI.md](./GEMINI.md)`。本檔案確保跨平台 Agent 工具（Google Antigravity 2.0 `agy`、OpenAI `codex`、OpenCode）在向上遍歷工作區時皆能一致載入專案規則。

## 快速檢查清單（Quick Checklist for Headless Runs）
1. **Skill 觸發**：遇到 PR / CL 審查時，優先讀取 `.agents/skills/payment-security-audit/SKILL.md`。
2. **MCP 驗證**：遇到 SQL 語句時，呼叫 `sqlite-schema-mcp` 伺服器驗證 `orders` 與 `payments` 資料表結構。
3. **Sub-agent 分工**：將跨檔案攻擊鏈追蹤與測試覆蓋率盤點委派給 `research` 或專案定義之子代理。
4. **Hooks 配合**：所有工具呼叫均受 `.agents/hooks.json` 生命週期攔截器監控，請勿嘗試存取 `.env` 或執行未授權之破壞性指令。
